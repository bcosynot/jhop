
# JHOP - Sleep tracking and Alarm Management Application

JHOP is a Python-based web application designed to help users log their sleep patterns and manage alarms dynamically.
It uses FastAPI as the backend framework, SQLite for storing data, and Nix/Poetry for reproducible development and builds.

---

## Features

- **Sleep Tracking**: Log sleep times with different categories (e.g., "night sleep" or "nap") and store them in a database for future reference.
- **Dynamic Alarm Management**: Automatically calculates alarm times based on sleep patterns or allows users to set them manually.
- **Predefined Defaults**:
  - A default alarm time of 9:00 AM if insufficient sleep data is provided.
  - Expected durations for specific sleep types (e.g., 7 hours for "night").
- **Endpoints**:
  - Log sleep activity (`POST /sleep`).
  - Retrieve the latest sleep entry (`GET /sleep/latest`).
  - Manage alarms (`POST`, `GET`, `DELETE /alarm`).

---

## Getting Started

### Prerequisites

- Python 3.12+
- Nix (for reproducible builds and shells)
- Poetry (dependency management)

### Installation

#### Using Nix:
1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd jhop
   ```
2. Enter the development shell:
   ```bash
   nix develop
   ```
3. Run the application:
   ```bash
   poetry run start
   ```

---

## Configuration

- **Database Path**: Set using the environment variable `JHOP_DB_PATH` (defaults to `data/sleeps.db`).
- **Development Shells**:
  - `default`: Installs application and dependencies.
  - `poetry`: For working with `pyproject.toml` and modifying dependencies.

---

## Project Structure

- `main.py`: Contains the application logic and endpoints.
- `tests/`: Directory to write and run test cases.
- `pyproject.toml`: Poetry configuration file.
- `flake.nix`: Nix configuration for reproducible builds.

---

## Testing

JHOP uses `pytest` and `pytest-asyncio` for testing. To run tests:
```bash
pytest
```

---

## Contributing

Contributions are welcome! To get started:
1. Fork this repository.
2. Create a feature branch (`git checkout -b feature-name`).
3. Commit changes and submit a pull request.

