# Installation

## Prerequisites

- Python 3.9 or higher
- pip package manager
- Git (for cloning the repository)

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/xsarena.git
cd xsarena
```

### 2. Set up Virtual Environment (Recommended)

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -e ".[dev]"
```

### 4. Verify Installation

```bash
xsarena --help
```

## Configuration

After installation, you may need to configure your API keys and settings:

1. Create a configuration file at `.xsarena/config.yml`
2. Add your API keys and backend settings
3. Run `xsarena ops health fix-run` to verify the setup