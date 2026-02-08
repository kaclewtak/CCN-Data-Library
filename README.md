# 4_capstone Project Environment

This directory contains the unified development environment for the Capstone project. It is managed using **[uv](https://github.com/astral-sh/uv)**.

## Quick Start

### 1. Install `uv`
If you do not have `uv` installed, run the installation command for your OS:
- **Mac/Linux:** `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Windows:** `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`

### 2. Sync the Environment
Navigate to this folder and sync the project. This will automatically download Python 3.13 and all required packages into a local `.venv` folder.

If you are on windows you will have to first start VSCode in WSL mode. This can be done by going to the bottom-left of the window and clicking on the two arrows `><` and pressing "Connect to WSL". This will restart VSCode in WSL mode and ensure that the next steps all work.

Otherwise there will be a conflict where the below command in WSL will result in the `.venv` python file path being different from what VSCode, running in powershell mode, will expect. 

```bash
cd scripts/4_capstone
uv sync
```


---

## VS Code Setup

To ensure linting, formatting, and imports work correctly, you must open this specific folder as your workspace root.

1. Open VS Code.
2. Go to **File > Open Folder...**
3. Select `CCN-Data-Library/scripts/4_capstone`.

### Recommended Extensions

When you open this folder, VS Code should prompt you to install the recommended extensions. If not, manually install:

* **Python** (`ms-python.python`)
* **Ruff** (`charliermarsh.ruff`) - *Fast linting*
* **Black Formatter** (`ms-python.black-formatter`) - *Auto-formatting*
* **Isort** (`ms-python.isort`) - *Import sorting*

**Note:** The `.vscode/settings.json` file in this directory is configured to automatically format your code and sort imports every time you save a file.

---

## Data Science & QA Stack

I have pre-installed a unified stack for EDA and QA/QC.

### Core Libraries

* **pandas & numpy**: Base level data handling and manipulation
* **matplotlib & seaborn**: Plotting
* **scipy & networkx**: Scientific computing and graph analysis.

### QA & Validation

* **pandera**: A statistical validation library for pandas. This can be used to define schemas and validate data quality (e.g., ensuring columns have no nulls or fall within a specific range).

* **Klib**: Python library for importing, cleaning, analyzing and preprocessing data. Can be used moreso for cleaning data.

* **Great-Expectations**: Experimental package for data quality *enforcement*. It's a more complex profiler meant for production pipelines.

### Interactive EDA

* **JupyterLab**: Interactive notebooks.
* **ydata-profiling**: A library for generating high-density EDA reports.

#### How to Generate a QA Report

You can generate a visual data quality report by running the following inside a Jupyter notebook:

```python
import pandas as pd
import sweetviz as sv

# Load your data
df = pd.read_csv("data.csv")

# Generate and show report
report = sv.analyze(df)
report.show_html("data_quality_report.html")

```

An example notebook is provided (`exploration.ipynb`) which uses existing data from within this repo.

---

## Common Commands For UV (as a just-in-case)

| Goal | Command |
| --- | --- |
| **Run a script** | `uv run my_script.py` |
| **Run Tests** | `uv run pytest` |
| **Start Jupyter** | `uv run jupyter lab` |
| **Add a package** | `uv add package_name` |
| **Add a dev tool** | `uv add --dev package_name` |

### Using Jupyter in VS Code

1. Create or open a `.ipynb` file.
2. Click **Select Kernel** at the top right.
3. Choose **Python 3.13 (4_capstone)** or look for the path ending in `.venv`.
