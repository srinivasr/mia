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

    const targetColor = new THREE.Color();
    const currentColor = new THREE.Color();
    let targetSpeed = 0.001;
    let currentSpeed = 0.001;
    let targetScale = 1.0;
    let currentScale = 1.0;
    let targetBreathIntensity = 0.3;
    let currentBreathIntensity = 0.3;

    const stateConfigs: Record<
        string,
        { color: number; speed: number; scale: number; breathIntensity: number }
    > = {
        Idle: {
            color: 0x4ae5ff,
            speed: 0.003,
            scale: 1.0,
            breathIntensity: 0.3,
        },
        Listening: {
            color: 0x00ffff,
            speed: 0.012,
            scale: 1.05,
            breathIntensity: 0.5,
        },
        Thinking: {
            color: 0xb34aff,
            speed: 0.015,
            scale: 1.0,
            breathIntensity: 0.6,
        },
        Speaking: {
            color: 0xffffff,
            speed: 0.006,
            scale: 1.1,
            breathIntensity: 0.8,
        },
        Searching: {
            color: 0x00ff88,
            speed: 0.018,
            scale: 1.0,
            breathIntensity: 0.5,
        },
        ExecutingTool: {
            color: 0xffaa00,
            speed: 0.012,
            scale: 1.0,
            breathIntensity: 0.4,
        },
        Error: {
            color: 0xff3333,
            speed: 0.03,
            scale: 0.95,
            breathIntensity: 1.0,
        },
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

    // ── GLSL Shaders ──────────────────────────────────────────────────
    const vertexShader = /* glsl */ `
        attribute float aSize;
        attribute float aPhase;
        attribute float aOpacity;

        uniform float uTime;
        uniform float uBreathIntensity;
        uniform float uPixelRatio;

        varying float vOpacity;
        varying float vDistFromCenter;

        void main() {
            float dist = length(position);
            vDistFromCenter = clamp(dist / 60.0, 0.0, 1.0);

            // Each particle breathes at its own rhythm
            float breath = sin(uTime * 2.0 + aPhase) * 0.5 + 0.5;
            float sizeMod = 1.0 + breath * uBreathIntensity;

            // Particles closer to center render larger
            float centerBoost = 1.0 + (1.0 - vDistFromCenter) * 0.5;

            // Opacity pulses with the breath
            vOpacity = aOpacity * (0.6 + breath * 0.4);

            vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
            gl_PointSize = aSize * sizeMod * centerBoost * uPixelRatio * (200.0 / -mvPosition.z);
            gl_Position = projectionMatrix * mvPosition;
        }
    `;

    const fragmentShader = /* glsl */ `
        uniform vec3 uColor;

        varying float vOpacity;
        varying float vDistFromCenter;

        void main() {
            // Soft circular glow instead of a hard square
            float d = length(gl_PointCoord - vec2(0.5));
            if (d > 0.5) discard;

            float alpha = 1.0 - smoothstep(0.0, 0.5, d);
            alpha *= alpha;  // quadratic falloff for softer edges

            // Core particles glow brighter
            float coreBrightness = 1.0 + (1.0 - vDistFromCenter) * 0.3;
            vec3 finalColor = uColor * coreBrightness;

            gl_FragColor = vec4(finalColor, alpha * vOpacity);
        }
    `;

    let resizeObserver: ResizeObserver;

    onMount(() => {
        initScene();
        animate();

        resizeObserver = new ResizeObserver((entries) => {
            for (let entry of entries) {
                const { width, height } = entry.contentRect;
                if (width && height) {
                    onWindowResize(width, height);
                }
            }
        });
        resizeObserver.observe(container);
    });

    onDestroy(() => {
        if (resizeObserver && container) resizeObserver.unobserve(container);
        if (animationId) cancelAnimationFrame(animationId);
        if (renderer) renderer.dispose();
        gridFloor = null;
        floorGlow = null;
        equatorialRing = null;
        tiltedRing = null;
        polarRing = null;
        pulseRing = null;
    });

    function createGridFloor() {
        const size = 400;
        const divisions = 80;
        const step = size / divisions;
        const half = size / 2;

        const positions: number[] = [];
        const colors: number[] = [];
        const centerColor = new THREE.Color(0x00d4ff);
        const edgeColor = new THREE.Color(0x001a33);

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
        geometry.setAttribute(
            "position",
            new THREE.Float32BufferAttribute(positions, 3),
        );
        geometry.setAttribute(
            "color",
            new THREE.Float32BufferAttribute(colors, 3),
        );

        const material = new THREE.LineBasicMaterial({
            vertexColors: true,
            transparent: true,
            opacity: 0.1,
            depthWrite: false,
        });

        gridFloor = new THREE.LineSegments(geometry, material);
        gridFloor.position.y = -75;
        scene.add(gridFloor);

        const glowCanvas = document.createElement("canvas");
        glowCanvas.width = 256;
        glowCanvas.height = 256;
        const ctx = glowCanvas.getContext("2d")!;
        const gradient = ctx.createRadialGradient(128, 128, 0, 128, 128, 128);
        gradient.addColorStop(0, "rgba(0, 180, 255, 0.25)");
        gradient.addColorStop(0.3, "rgba(0, 100, 200, 0.08)");
        gradient.addColorStop(1, "rgba(0, 0, 0, 0)");
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, 256, 256);

        const glowTexture = new THREE.CanvasTexture(glowCanvas);
        const glowMaterial = new THREE.SpriteMaterial({
            map: glowTexture,
            transparent: true,
            blending: THREE.AdditiveBlending,
            depthWrite: false,
            opacity: 0.5,
        });
        floorGlow = new THREE.Sprite(glowMaterial);
        floorGlow.position.set(0, -73, 0);
        floorGlow.scale.set(160, 160, 1);
        scene.add(floorGlow);
    }

    function createOrbitalRings() {
        const ringGeo = (radius: number, tube: number) =>
            new THREE.TorusGeometry(radius, tube, 24, 120);

        const ringMat = (color: number, opacity: number) =>
            new THREE.MeshBasicMaterial({
                color,
                transparent: true,
                opacity,
                blending: THREE.AdditiveBlending,
                depthWrite: false,
                side: THREE.DoubleSide,
            });

        equatorialRing = new THREE.Mesh(
            ringGeo(65, 0.08),
            ringMat(0x4ae5ff, 0.4),
        );
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

        const pulseGeo = new THREE.RingGeometry(2, 5, 64);
        const pulseMat = new THREE.MeshBasicMaterial({
            color: 0x4ae5ff,
            transparent: true,
            opacity: 0,
            side: THREE.DoubleSide,
            blending: THREE.AdditiveBlending,
            depthWrite: false,
        });
        pulseRing = new THREE.Mesh(pulseGeo, pulseMat);
        pulseRing.position.y = 5;
        pulseRing.rotation.x = -Math.PI / 2;
        scene.add(pulseRing);
    }

    function initScene() {
        scene = new THREE.Scene();

        camera = new THREE.PerspectiveCamera(
            45,
            window.innerWidth / window.innerHeight,
            1,
            1000,
        );
        camera.position.z = 350;
        renderer = new THREE.WebGLRenderer({
            antialias: true,
            alpha: true,
            powerPreference: "high-performance",
        });

        container.appendChild(renderer.domElement);

        // ── Particle geometry ─────────────────────────────────────────
        const particleCount = 100000;
        const geometry = new THREE.BufferGeometry();
        const positions = new Float32Array(particleCount * 3);
        const sizes = new Float32Array(particleCount);
        const phases = new Float32Array(particleCount);
        const opacities = new Float32Array(particleCount);
        const radius = 60;

        for (let i = 0; i < particleCount; i++) {
            const theta = Math.random() * Math.PI * 2;
            const phi = Math.acos(Math.random() * 2 - 1);
            const r = radius - Math.random() * 15;

            positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
            positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
            positions[i * 3 + 2] = r * Math.cos(phi);

            // Per-particle variation
            sizes[i] = 0.5 + Math.random() * 2.5; // 0.5 – 3.0
            phases[i] = Math.random() * Math.PI * 2; // desync breathing
            opacities[i] = 0.4 + Math.random() * 0.6; // 0.4 – 1.0
        }

        geometry.setAttribute(
            "position",
            new THREE.BufferAttribute(positions, 3),
        );
        geometry.setAttribute("aSize", new THREE.BufferAttribute(sizes, 1));
        geometry.setAttribute("aPhase", new THREE.BufferAttribute(phases, 1));
        geometry.setAttribute(
            "aOpacity",
            new THREE.BufferAttribute(opacities, 1),
        );

        // ── Custom shader material ────────────────────────────────────
        shaderMaterial = new THREE.ShaderMaterial({
            vertexShader,
            fragmentShader,
            uniforms: {
                uTime: { value: 0.0 },
                uColor: { value: new THREE.Color(0x4ae5ff) },
                uBreathIntensity: { value: 0.3 },
                uPixelRatio: { value: Math.min(window.devicePixelRatio, 2) },
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

    let lastTime = performance.now();

    function animate() {
        animationId = requestAnimationFrame(animate);

        const currentTime = performance.now();
        // Normalize delta time to 60fps (~16.66ms per frame)
        // This ensures the orb rotates at the exact same speed mian if the framerate lags
        const dt = (currentTime - lastTime) / 16.666;
        lastTime = currentTime;

        // Smooth lerped transitions (also scaled by dt for smooth state changes)
        currentColor.lerp(targetColor, 0.15 * dt);
        currentSpeed += (targetSpeed - currentSpeed) * 0.15 * dt;
        currentScale += (targetScale - currentScale) * 0.2 * dt;
        currentBreathIntensity +=
            (targetBreathIntensity - currentBreathIntensity) * 0.1 * dt;

        let scaleMod = currentScale;
        if ($currentState === "Speaking") {
            scaleMod += Math.sin(Date.now() * 0.01) * 0.03;
        }

        particleSystem.scale.set(scaleMod, scaleMod, scaleMod);

        // Rings breathe with the orb — same scale so they stay connected
        if (equatorialRing)
            equatorialRing.scale.set(scaleMod, scaleMod, scaleMod);
        if (tiltedRing) tiltedRing.scale.set(scaleMod, scaleMod, scaleMod);
        if (polarRing) polarRing.scale.set(scaleMod, scaleMod, scaleMod);

        // Drive the shader
        shaderMaterial.uniforms.uTime.value = Date.now() * 0.001;
        shaderMaterial.uniforms.uColor.value.copy(currentColor);
        shaderMaterial.uniforms.uBreathIntensity.value = currentBreathIntensity;

        // Rings track the orb color with brightness layers for depth
        if (equatorialRing)
            (equatorialRing.material as THREE.MeshBasicMaterial).color.copy(
                currentColor,
            );
        if (tiltedRing)
            (tiltedRing.material as THREE.MeshBasicMaterial).color
                .copy(currentColor)
                .multiplyScalar(0.65);
        if (polarRing)
            (polarRing.material as THREE.MeshBasicMaterial).color
                .copy(currentColor)
                .multiplyScalar(0.4);
        if (pulseRing)
            (pulseRing.material as THREE.MeshBasicMaterial).color.copy(
                currentColor,
            );

        // Apply frame-rate independent rotation
        particleSystem.rotation.y += currentSpeed * dt;
        particleSystem.rotation.x += currentSpeed * 0.5 * dt;

        // ── Orbital ring animation ────────────────────────────────────
        if (equatorialRing) equatorialRing.rotation.z += 0.003 * dt;
        if (tiltedRing) {
            tiltedRing.rotation.y += 0.005 * dt;
            tiltedRing.rotation.x += 0.001 * dt;
        }
        if (polarRing) polarRing.rotation.y -= 0.004 * dt;

        // ── Radar pulse animation ─────────────────────────────────────
        if (pulseActive && pulseRing) {
            pulseTimer += 0.025 * dt;
            const s = 1 + pulseTimer * 5;
            const o = Math.max(0, 1 - pulseTimer * 1.2);
            pulseRing.scale.set(s, s, s);
            pulseRing.material.opacity = o * 0.6;
            if (pulseTimer >= 1) {
                pulseActive = false;
                pulseRing.scale.set(1, 1, 1);
                pulseRing.material.opacity = 0;
            }
        }

        // ── Grid floor subtle animation ───────────────────────────────
        if (gridFloor) {
            gridFloor.position.z = Math.sin(Date.now() * 0.00008) * 1.5;
        }
        if (floorGlow) {
            const pulse = Math.sin(Date.now() * 0.001) * 0.1 + 0.9;
            floorGlow.material.opacity = 0.4 * pulse;
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

<div bind:this={container} class="canvas-container"></div>

<style>
    .canvas-container {
        position: absolute;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        overflow: hidden;
        pointer-events: none;
        z-index: 10;
    }
</style>
