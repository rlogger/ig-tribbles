{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    # Python environment
    python311
    python311Packages.pip
    python311Packages.virtualenv
    python311Packages.ipython

    # Python dev tools
    python311Packages.black
    python311Packages.isort
    python311Packages.debugpy

    # Discord bot dependencies (available in nixpkgs)
    python311Packages.discordpy
    python311Packages.pandas
    python311Packages.matplotlib
    python311Packages.aiosqlite
    python311Packages.python-dotenv

    # Dev tools
    neovim
    git
    curl
    gcc
    gnumake
    nodejs
    ripgrep
    fd
    lazygit
    tree
    wget

    # Deployment
    docker
    docker-compose
  ];

  shellHook = ''
    echo "=================================================="
    echo " Instagram Follower Tracker - Discord Bot"
    echo "=================================================="

    # Setup virtual environment for any extra packages
    if [ ! -d .venv ]; then
      echo "Creating Python virtual environment..."
      python -m venv .venv
    fi

    source .venv/bin/activate

    # Install any packages not in nixpkgs
    pip install --quiet --upgrade pip 2>/dev/null
    pip install --quiet -r requirements.txt 2>/dev/null || true

    # Neovim config setup (from your nvim-config)
    export NVIM_CONFIG_DIR="$HOME/.config/nvim-nix-shell"
    mkdir -p "$NVIM_CONFIG_DIR"

    REPO_URL="https://raw.githubusercontent.com/rlogger/nvim-config/refs/heads/main/init.lua"
    CONFIG_FILE="$NVIM_CONFIG_DIR/init.lua"

    if [ ! -f "$CONFIG_FILE" ] || [ $(find "$CONFIG_FILE" -mtime +1 2>/dev/null | wc -l) -gt 0 ]; then
      echo ""
      echo "Downloading custom Neovim config..."
      if curl -fsSL "$REPO_URL" -o "$CONFIG_FILE" 2>/dev/null; then
        echo "Config downloaded successfully"
      else
        echo "Using cached/default Neovim config"
      fi
    fi

    # Aliases
    alias nvim='nvim -u "$NVIM_CONFIG_DIR/init.lua"'
    alias vim='nvim -u "$NVIM_CONFIG_DIR/init.lua"'
    alias vi='nvim -u "$NVIM_CONFIG_DIR/init.lua"'
    alias python='python3'
    alias pip='pip3'
    alias lg='lazygit'
    alias gs='git status'
    alias gd='git diff'
    alias ga='git add'
    alias gc='git commit'
    alias gp='git push'
    alias gl='git pull'

    # Bot-specific aliases
    alias bot='python bot.py'
    alias dc='docker-compose'
    alias dcup='docker-compose up -d'
    alias dcdown='docker-compose down'
    alias dclogs='docker-compose logs -f'

    # XDG directories
    export XDG_CONFIG_HOME="''${XDG_CONFIG_HOME:-$HOME/.config}"
    export XDG_DATA_HOME="''${XDG_DATA_HOME:-$HOME/.local/share}"
    export XDG_CACHE_HOME="''${XDG_CACHE_HOME:-$HOME/.cache}"

    mkdir -p "$XDG_DATA_HOME/nvim/site/pack"
    mkdir -p "$XDG_CACHE_HOME/nvim"

    export PYTHON_PATH="$(which python3)"

    echo ""
    echo " Project: ig-discord (Instagram Follower Tracker)"
    echo " Neovim config: $NVIM_CONFIG_DIR/init.lua"
    echo ""
    echo " Quick Start:"
    echo "   bot              - Run the Discord bot"
    echo "   nvim bot.py      - Edit bot code"
    echo "   lg               - LazyGit"
    echo ""
    echo " Docker Commands:"
    echo "   dcup             - Start bot in Docker"
    echo "   dcdown           - Stop bot"
    echo "   dclogs           - View logs"
    echo ""
    echo " Bot Commands (once running):"
    echo "   /demo            - Load sample data"
    echo "   /upload          - Upload CSV file"
    echo "   /stats           - View dashboard"
    echo ""
    echo " Setup:"
    echo "   1. cp .env.example .env"
    echo "   2. Add your DISCORD_TOKEN to .env"
    echo "   3. Run: bot (or python bot.py)"
    echo ""
    echo "=================================================="
  '';

  PROMPT_COLOR = "1;35m";  # Purple for this project
}
