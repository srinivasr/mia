<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import * as THREE from "three";
    import { currentState } from "../stores/miaState";

    let container: HTMLDivElement;
    let animationId: number;
    let renderer: THREE.WebGLRenderer;
    let scene: THREE.Scene;
    let camera: THREE.PerspectiveCamera;
    let particleSystem: THREE.Points;
    let shaderMaterial: THREE.ShaderMaterial;
    let gridFloor: THREE.LineSegments | null = null;
    let floorGlow: THREE.Sprite | null = null;
    let equatorialRing: THREE.Mesh | null = null;
    let tiltedRing: THREE.Mesh | null = null;
    let polarRing: THREE.Mesh | null = null;
    let pulseRing: THREE.Mesh | null = null;
    let pulseActive = false;
    let pulseTimer = 0;
    let previousState: string = "Idle";

    const PARTICLE_COUNT = 15000;
    const ORB_RADIUS = 60;

    let originPositions: Float32Array;
    let currentPositions: Float32Array;
    // Velocities for spring physics
    let velocities: Float32Array;

    // Projected mouse in world-space (z = 0 plane)
    const mouse3D = new THREE.Vector3();
    const raycaster = new THREE.Raycaster();
    const mousNDC = new THREE.Vector2(-9999, -9999); // off-screen initially
    // Interaction mode toggled by right-click
    type InteractMode = "repel" | "attract" | "swirl";
    let interactMode: InteractMode = "repel";

    const SPRING_K = 0.035;
    const DAMPING = 0.82;
    const CURSOR_RADIUS = 55;
    const FORCE_STRENGTH = 6.0;

    const targetColor  = new THREE.Color();
    const currentColor = new THREE.Color();
    let targetSpeed           = 0.001;
    let currentSpeed          = 0.001;
    let targetScale           = 1.0;
    let currentScale          = 1.0;
    let targetBreathIntensity = 0.3;
    let currentBreathIntensity = 0.3;

    const stateConfigs: Record<
        string,
        { color: number; speed: number; scale: number; breathIntensity: number }
    > = {
        Initializing: { color: 0xff00ff, speed: 0.02,   scale: 1.2,  breathIntensity: 1.0 },
        Idle:         { color: 0x4ae5ff, speed: 0.001,  scale: 1.0,  breathIntensity: 0.3 },
        Listening:    { color: 0x00ffff, speed: 0.005,  scale: 1.05, breathIntensity: 0.5 },
        Thinking:     { color: 0xb34aff, speed: 0.006,  scale: 1.0,  breathIntensity: 0.6 },
        Speaking:     { color: 0xffffff, speed: 0.002,  scale: 1.1,  breathIntensity: 0.8 },
        Searching:    { color: 0x00ff88, speed: 0.008,  scale: 1.0,  breathIntensity: 0.5 },
        ExecutingTool:{ color: 0xffaa00, speed: 0.005,  scale: 1.0,  breathIntensity: 0.4 },
        Error:        { color: 0xff3333, speed: 0.015,  scale: 0.95, breathIntensity: 1.0 },
    };

    $: {
        const config =
            stateConfigs[$currentState as keyof typeof stateConfigs] ||
            stateConfigs["Idle"];
        targetColor.setHex(config.color);
        targetSpeed = config.speed;
        targetScale = config.scale;
        targetBreathIntensity = config.breathIntensity;

        if (
            previousState !== $currentState &&
            ($currentState === "Listening" || $currentState === "Speaking")
        ) {
            pulseActive = true;
            pulseTimer = 0;
        }
        previousState = $currentState;
    }

    // NOTE: positions are updated on the CPU; the shader only handles
    //       per-particle breathing, sizing, and soft-glow rendering.
    const vertexShader = /* glsl */ `
        attribute float aSize;
        attribute float aPhase;
        attribute float aOpacity;
        attribute float aDisplace;

        uniform float uTime;
        uniform float uBreathIntensity;
        uniform float uPixelRatio;

        varying float vOpacity;
        varying float vDistFromCenter;
        varying float vDisplace;

        void main() {
            float dist = length(position);
            vDistFromCenter = clamp(dist / 60.0, 0.0, 1.0);
            vDisplace = aDisplace;

            float breath = sin(uTime * 2.0 + aPhase) * 0.5 + 0.5;
            float sizeMod = 1.0 + breath * uBreathIntensity;
            float centerBoost = 1.0 + (1.0 - vDistFromCenter) * 0.5;

            // Displaced particles appear brighter / larger
            float dispBoost = 1.0 + aDisplace * 1.8;

            vOpacity = aOpacity * (0.6 + breath * 0.4);

            vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
            gl_PointSize = aSize * sizeMod * centerBoost * dispBoost * uPixelRatio * (200.0 / -mvPosition.z);
            gl_Position = projectionMatrix * mvPosition;
        }
    `;

    const fragmentShader = /* glsl */ `
        uniform vec3 uColor;

        varying float vOpacity;
        varying float vDistFromCenter;
        varying float vDisplace;

        void main() {
            float d = length(gl_PointCoord - vec2(0.5));
            if (d > 0.5) discard;

            float alpha = 1.0 - smoothstep(0.0, 0.5, d);
            alpha *= alpha;

            float coreBrightness = 1.0 + (1.0 - vDistFromCenter) * 0.3;
            // Displaced particles get a bright halo
            float dispGlow = 1.0 + vDisplace * 1.5;
            vec3 finalColor = uColor * coreBrightness * dispGlow;

            gl_FragColor = vec4(finalColor, alpha * vOpacity);
        }
    `;

    let resizeObserver: ResizeObserver;

    onMount(() => {
        initScene();
        animate();

        window.addEventListener("mousemove", onMouseMove);
        window.addEventListener("contextmenu", onContextMenu);

        resizeObserver = new ResizeObserver((entries) => {
            for (let entry of entries) {
                const { width, height } = entry.contentRect;
                if (width && height) onWindowResize(width, height);
            }
        });
        resizeObserver.observe(container);
    });

    onDestroy(() => {
        if (resizeObserver && container) resizeObserver.unobserve(container);
        if (animationId) cancelAnimationFrame(animationId);
        if (renderer) renderer.dispose();
        window.removeEventListener("mousemove", onMouseMove);
        window.removeEventListener("contextmenu", onContextMenu);
        gridFloor = null; floorGlow = null;
        equatorialRing = null; tiltedRing = null;
        polarRing = null; pulseRing = null;
    });

    function onMouseMove(e: MouseEvent) {
        mousNDC.x =  (e.clientX / window.innerWidth)  * 2 - 1;
        mousNDC.y = -(e.clientY / window.innerHeight) * 2 + 1;
    }

    function onContextMenu(e: MouseEvent) {
        e.preventDefault();
        const modes: InteractMode[] = ["repel", "attract", "swirl"];
        const idx = modes.indexOf(interactMode);
        interactMode = modes[(idx + 1) % modes.length];
    }

    const _ray_origin = new THREE.Vector3();
    const _ray_dir    = new THREE.Vector3();
    function projectMouseToWorld(): THREE.Vector3 {
        raycaster.setFromCamera(mousNDC, camera);
        // Find where the ray hits the plane z = particleSystem.position.z (≈0)
        const t = (particleSystem.position.z - raycaster.ray.origin.z) / raycaster.ray.direction.z;
        mouse3D.copy(raycaster.ray.origin).addScaledVector(raycaster.ray.direction, t);
        // Transform into local particle-system space
        particleSystem.worldToLocal(mouse3D);
        return mouse3D;
    }

    function fibonacciSphere(count: number, baseRadius: number): Float32Array {
        const positions = new Float32Array(count * 3);
        const golden = Math.PI * (3 - Math.sqrt(5)); // golden angle ≈ 2.399 rad
        for (let i = 0; i < count; i++) {
            const y   = 1 - (i / (count - 1)) * 2;          // -1 → 1
            const r   = Math.sqrt(1 - y * y);
            const phi = i * golden;
            
            let r_actual = baseRadius - (Math.random() * 8); // 8 units of inner shell thickness
            
            const randStray = Math.random();
            if (randStray > 0.92) {
                // Outer strays
                r_actual = baseRadius + 2 + Math.random() * 25; 
            } else if (randStray < 0.05) {
                // Deep core strays
                r_actual = baseRadius * (0.3 + Math.random() * 0.5);
            }

            positions[i * 3]     = Math.cos(phi) * r * r_actual;
            positions[i * 3 + 1] = y * r_actual;
            positions[i * 3 + 2] = Math.sin(phi) * r * r_actual;
        }
        return positions;
    }

    function createGridFloor() {
        const size = 400, divisions = 80, step = size / divisions, half = size / 2;
        const positions: number[] = [];
        const colors: number[]    = [];
        const centerColor = new THREE.Color(0x00d4ff);
        const edgeColor   = new THREE.Color(0x001a33);

        for (let i = 0; i <= divisions; i++) {
            const x = -half + i * step;
            const t = Math.abs(x) / half;
            const c = centerColor.clone().lerp(edgeColor, t);
            positions.push(x, 0, -half, x, 0, half);
            colors.push(c.r, c.g, c.b, c.r, c.g, c.b);
        }
        for (let i = 0; i <= divisions; i++) {
            const z = -half + i * step;
            const t = Math.abs(z) / half;
            const c = centerColor.clone().lerp(edgeColor, t);
            positions.push(-half, 0, z, half, 0, z);
            colors.push(c.r, c.g, c.b, c.r, c.g, c.b);
        }

        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
        geometry.setAttribute("color",    new THREE.Float32BufferAttribute(colors, 3));

        gridFloor = new THREE.LineSegments(geometry, new THREE.LineBasicMaterial({
            vertexColors: true, transparent: true, opacity: 0.1, depthWrite: false,
        }));
        gridFloor.position.y = -75;
        scene.add(gridFloor);

        const glowCanvas = document.createElement("canvas");
        glowCanvas.width = glowCanvas.height = 256;
        const ctx = glowCanvas.getContext("2d")!;
        const gradient = ctx.createRadialGradient(128, 128, 0, 128, 128, 128);
        gradient.addColorStop(0,   "rgba(0, 180, 255, 0.25)");
        gradient.addColorStop(0.3, "rgba(0, 100, 200, 0.08)");
        gradient.addColorStop(1,   "rgba(0, 0, 0, 0)");
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, 256, 256);

        floorGlow = new THREE.Sprite(new THREE.SpriteMaterial({
            map: new THREE.CanvasTexture(glowCanvas),
            transparent: true,
            blending: THREE.AdditiveBlending,
            depthWrite: false,
            opacity: 0.5,
        }));
        floorGlow.position.set(0, -73, 0);
        floorGlow.scale.set(160, 160, 1);
        scene.add(floorGlow);
    }

    function createOrbitalRings() {
        const ringGeo = (radius: number, tube: number) =>
            new THREE.TorusGeometry(radius, tube, 24, 120);
        const ringMat = (color: number, opacity: number) =>
            new THREE.MeshBasicMaterial({
                color, transparent: true, opacity,
                blending: THREE.AdditiveBlending,
                depthWrite: false, side: THREE.DoubleSide,
            });

        equatorialRing = new THREE.Mesh(ringGeo(65, 0.08), ringMat(0x4ae5ff, 0.4));
        equatorialRing.position.y = 5;
        scene.add(equatorialRing);

        tiltedRing = new THREE.Mesh(ringGeo(70, 0.06), ringMat(0x4ae5ff, 0.3));
        tiltedRing.position.y = 5;
        tiltedRing.rotation.x = 0.7;
        tiltedRing.rotation.z = 0.5;
        scene.add(tiltedRing);

        polarRing = new THREE.Mesh(ringGeo(62, 0.05), ringMat(0x4ae5ff, 0.2));
        polarRing.position.y = 5;
        polarRing.rotation.x = Math.PI / 2;
        scene.add(polarRing);

        pulseRing = new THREE.Mesh(
            new THREE.RingGeometry(2, 5, 64),
            new THREE.MeshBasicMaterial({
                color: 0x4ae5ff, transparent: true, opacity: 0,
                side: THREE.DoubleSide,
                blending: THREE.AdditiveBlending, depthWrite: false,
            })
        );
        pulseRing.position.y = 5;
        pulseRing.rotation.x = -Math.PI / 2;
        scene.add(pulseRing);
    }

    function initScene() {
        scene  = new THREE.Scene();
        camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 1, 1000);
        camera.position.z = 350;

        renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "high-performance" });
        container.appendChild(renderer.domElement);

        originPositions  = fibonacciSphere(PARTICLE_COUNT, ORB_RADIUS);
        currentPositions = new Float32Array(originPositions);
        velocities       = new Float32Array(PARTICLE_COUNT * 3);

        const sizes      = new Float32Array(PARTICLE_COUNT);
        const phases     = new Float32Array(PARTICLE_COUNT);
        const opacities  = new Float32Array(PARTICLE_COUNT);
        const displaces  = new Float32Array(PARTICLE_COUNT); // displacement magnitude per particle

        for (let i = 0; i < PARTICLE_COUNT; i++) {
            sizes[i]     = 0.8 + Math.random() * 2.2;
            phases[i]    = Math.random() * Math.PI * 2;
            opacities[i] = 0.5 + Math.random() * 0.5;
            displaces[i] = 0;
        }

        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute("position", new THREE.BufferAttribute(currentPositions, 3));
        geometry.setAttribute("aSize",    new THREE.BufferAttribute(sizes, 1));
        geometry.setAttribute("aPhase",   new THREE.BufferAttribute(phases, 1));
        geometry.setAttribute("aOpacity", new THREE.BufferAttribute(opacities, 1));
        geometry.setAttribute("aDisplace",new THREE.BufferAttribute(displaces, 1));

        shaderMaterial = new THREE.ShaderMaterial({
            vertexShader,
            fragmentShader,
            uniforms: {
                uTime:            { value: 0.0 },
                uColor:           { value: new THREE.Color(0x4ae5ff) },
                uBreathIntensity: { value: 0.3 },
                uPixelRatio:      { value: Math.min(window.devicePixelRatio, 2) },
            },
            transparent: true,
            blending: THREE.AdditiveBlending,
            depthWrite: false,
        });

        particleSystem = new THREE.Points(geometry, shaderMaterial);
        particleSystem.position.y = 5;
        scene.add(particleSystem);
        currentColor.setHex(stateConfigs["Idle"].color);

        createGridFloor();
        createOrbitalRings();
    }

    const _diff   = new THREE.Vector3();
    const _force  = new THREE.Vector3();
    const _tangent = new THREE.Vector3();
    const _up      = new THREE.Vector3(0, 1, 0);
    let currentChaos = 0.0;

    function applyParticlePhysics(mouseLocal: THREE.Vector3) {
        const posAttr  = particleSystem.geometry.getAttribute("position") as THREE.BufferAttribute;
        const dispAttr = particleSystem.geometry.getAttribute("aDisplace") as THREE.BufferAttribute;
        const cr2 = CURSOR_RADIUS * CURSOR_RADIUS;

        const targetChaos = $currentState === "Initializing" ? 1.0 : 0.0;
        currentChaos += (targetChaos - currentChaos) * 0.05;

        for (let i = 0; i < PARTICLE_COUNT; i++) {
            const ix = i * 3, iy = ix + 1, iz = ix + 2;

            const px = currentPositions[ix];
            const py = currentPositions[iy];
            const pz = currentPositions[iz];

            const ox = originPositions[ix];
            const oy = originPositions[iy];
            const oz = originPositions[iz];

            const effectiveSpring = SPRING_K * (1.0 - currentChaos * 0.95);

            velocities[ix] += (ox - px) * effectiveSpring;
            velocities[iy] += (oy - py) * effectiveSpring;
            velocities[iz] += (oz - pz) * effectiveSpring;

            if (currentChaos > 0.01) {
                velocities[ix] += (Math.random() - 0.5) * 4.0 * currentChaos;
                velocities[iy] += (Math.random() - 0.5) * 4.0 * currentChaos;
                velocities[iz] += (Math.random() - 0.5) * 4.0 * currentChaos;
            }

            const dx = px - mouseLocal.x;
            const dy = py - mouseLocal.y;
            const dz = pz - mouseLocal.z;
            const d2 = dx * dx + dy * dy + dz * dz;

            let dispMag = 0;

            if (d2 < cr2 && d2 > 0.001) {
                const dist   = Math.sqrt(d2);
                const falloff = 1 - dist / CURSOR_RADIUS; // 0→1 as cursor gets closer
                const strength = falloff * falloff * FORCE_STRENGTH;

                if (interactMode === "repel") {
                    // Push away from cursor
                    const inv = strength / dist;
                    velocities[ix] += dx * inv;
                    velocities[iy] += dy * inv;
                    velocities[iz] += dz * inv;

                } else if (interactMode === "attract") {
                    // Pull toward cursor
                    const inv = strength / dist;
                    velocities[ix] -= dx * inv;
                    velocities[iy] -= dy * inv;
                    velocities[iz] -= dz * inv;

                } else {
                    // Swirl: apply tangential (cross-product) force
                    _diff.set(dx, dy, dz).normalize();
                    _tangent.crossVectors(_diff, _up).normalize();
                    velocities[ix] += _tangent.x * strength;
                    velocities[iy] += _tangent.y * strength;
                    velocities[iz] += _tangent.z * strength;
                }

                dispMag = falloff;
            }

            velocities[ix] *= DAMPING;
            velocities[iy] *= DAMPING;
            velocities[iz] *= DAMPING;

            currentPositions[ix] += velocities[ix];
            currentPositions[iy] += velocities[iy];
            currentPositions[iz] += velocities[iz];

            // Lerp the displacement attribute toward current value for smooth shader glow
            const prevDisp = dispAttr.getX(i);
            dispAttr.setX(i, prevDisp + (dispMag - prevDisp) * 0.15);
        }

        posAttr.needsUpdate  = true;
        dispAttr.needsUpdate = true;
    }

    let lastTime = performance.now();

    function animate() {
        animationId = requestAnimationFrame(animate);

        const now = performance.now();
        const dt  = (now - lastTime) / 16.666;
        lastTime  = now;

        // Smooth state transitions
        currentColor.lerp(targetColor, 0.15 * dt);
        currentSpeed             += (targetSpeed             - currentSpeed)             * 0.15 * dt;
        currentScale             += (targetScale             - currentScale)             * 0.20 * dt;
        currentBreathIntensity   += (targetBreathIntensity   - currentBreathIntensity)   * 0.10 * dt;

        let scaleMod = currentScale;
        if ($currentState === "Speaking") scaleMod += Math.sin(Date.now() * 0.01) * 0.03;

        particleSystem.scale.set(scaleMod, scaleMod, scaleMod);
        if (equatorialRing) equatorialRing.scale.set(scaleMod, scaleMod, scaleMod);
        if (tiltedRing)     tiltedRing.scale.set(scaleMod, scaleMod, scaleMod);
        if (polarRing)      polarRing.scale.set(scaleMod, scaleMod, scaleMod);

        shaderMaterial.uniforms.uTime.value            = Date.now() * 0.001;
        shaderMaterial.uniforms.uColor.value.copy(currentColor);
        shaderMaterial.uniforms.uBreathIntensity.value = currentBreathIntensity;

        // Ring colors
        if (equatorialRing) (equatorialRing.material as THREE.MeshBasicMaterial).color.copy(currentColor);
        if (tiltedRing)     (tiltedRing.material  as THREE.MeshBasicMaterial).color.copy(currentColor).multiplyScalar(0.65);
        if (polarRing)      (polarRing.material   as THREE.MeshBasicMaterial).color.copy(currentColor).multiplyScalar(0.4);
        if (pulseRing)      (pulseRing.material   as THREE.MeshBasicMaterial).color.copy(currentColor);

        // Slow global rotation (rotates the GROUP, but physics operate in local space)
        particleSystem.rotation.y += currentSpeed * dt;
        particleSystem.rotation.x += currentSpeed * 0.5 * dt;

        const mouseLocal = projectMouseToWorld();
        applyParticlePhysics(mouseLocal);

        if (equatorialRing) equatorialRing.rotation.z += 0.003 * dt;
        if (tiltedRing) {
            tiltedRing.rotation.y += 0.005 * dt;
            tiltedRing.rotation.x += 0.001 * dt;
        }
        if (polarRing) polarRing.rotation.y -= 0.004 * dt;

        if (pulseActive && pulseRing) {
            pulseTimer += 0.025 * dt;
            const s = 1 + pulseTimer * 5;
            const o = Math.max(0, 1 - pulseTimer * 1.2);
            pulseRing.scale.set(s, s, s);
            (pulseRing.material as THREE.MeshBasicMaterial).opacity = o * 0.6;
            if (pulseTimer >= 1) {
                pulseActive = false;
                pulseRing.scale.set(1, 1, 1);
                (pulseRing.material as THREE.MeshBasicMaterial).opacity = 0;
            }
        }

        if (gridFloor) gridFloor.position.z = Math.sin(Date.now() * 0.00008) * 1.5;
        if (floorGlow) {
            const pulse = Math.sin(Date.now() * 0.001) * 0.1 + 0.9;
            (floorGlow.material as THREE.SpriteMaterial).opacity = 0.4 * pulse;
        }

        renderer.render(scene, camera);
    }

    function onWindowResize(w: number, h: number) {
        if (!camera || !renderer) return;
        if (h === 0) h = 1;
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
        renderer.setSize(w, h);
    }
</script>

<!-- Tooltip showing current interaction mode -->
<div bind:this={container} class="canvas-container">
    <div class="mode-hint">
        {#if interactMode === "repel"}⊗ Repel{:else if interactMode === "attract"}⊕ Attract{:else}↺ Swirl{/if}
        <span class="hint-sub">right-click to cycle</span>
    </div>
</div>

<style>
    .canvas-container {
        position: absolute;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        overflow: hidden;
        pointer-events: auto;  /* must be auto so mousemove registers */
        z-index: 10;
    }

    .mode-hint {
        position: absolute;
        bottom: 24px;
        left: 50%;
        transform: translateX(-50%);
        color: rgba(74, 229, 255, 0.45);
        font-family: 'Inter', monospace;
        font-size: 11px;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        display: flex;
        gap: 8px;
        align-items: center;
        pointer-events: none;
        user-select: none;
    }

    .hint-sub {
        opacity: 0.45;
        font-size: 9px;
    }
</style>
