{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    # Tauri native dependencies
    pkg-config
    dbus
    openssl
    glib
    gtk3
    libsoup_3
    webkitgtk_4_1
    xdotool
    wtype
    wl-clipboard
    libappindicator
    librsvg
    libGL
    libGLU
    ffmpeg
    grim
    psmisc
    
    # Core project languages and toolchains
    cargo
    rustc
    gcc
    gnumake
    nodejs_22
    (python311.withPackages (ps: with ps; [ tkinter ]))
    portaudio
    zlib
    
    # Playwright driver
    playwright-driver.browsers
  ];

  shellHook = ''
    # Environment variables for Playwright
    export PLAYWRIGHT_BROWSERS_PATH=${pkgs.playwright-driver.browsers}
    export PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true
    export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

    # Add native libraries to LD_LIBRARY_PATH so Tauri, Cargo, and Python wheels can link against them
    export LD_LIBRARY_PATH=${pkgs.lib.makeLibraryPath (with pkgs; [
      openssl
      glib
      gtk3
      libsoup_3
      webkitgtk_4_1
      libappindicator
      dbus
      portaudio
      libGL
      libGLU
      zlib
      stdenv.cc.cc.lib
    ])}:$LD_LIBRARY_PATH
    
    echo "MIA Dev Env ready. Run './run.sh' to start."
  '';
}
