# Project Context — Terra Analog

## Project Goal

Build a web application that compares terrain
characteristics of Earth locations with selected
reference regions on Mars or the Moon.

## Product Scope

Users upload an Earth DEM file and select
a planetary reference region.

The application processes both datasets
and calculates terrain similarity.

No global Earth scanning.

## Architecture

- React frontend
- FastAPI backend
- Rasterio for DEM processing
- NumPy and SciPy for numerical calculations

## Backend Responsibilities

- File validation
- DEM preprocessing
- Resolution harmonization
- Terrain feature extraction
- Similarity calculations
- API responses

## Frontend Responsibilities

- User interface
- Planet selection
- Reference region selection
- DEM upload
- Results visualization
- Error and warning display

## Initial Terrain Metrics

1. Relative relief
2. Slope distribution
3. Surface roughness
4. Terrain morphology

## API

POST /analyze

See docs/api-contract.md.

## Team Responsibilities

Backend Lead:
- backend/
- Terrain processing
- Similarity algorithm
- API

Frontend & Data Lead:
- frontend/
- User interface
- Data source research
- Reference datasets

## Development Rules

- Keep backend and frontend responsibilities separate.
- Follow the API contract.
- Avoid unnecessary dependencies.
- Do not rewrite working code without a reason.
- Test changes before committing.
- Never commit secrets or API keys.

## AI Coding Rules

- Work only on the requested task.
- Do not modify unrelated files.
- Explain important changes.
- Keep implementation simple.
- Do not introduce unnecessary abstractions.
- Follow the existing project architecture.

## Current Status

Planning and preparation only.
Application development starts at the hackathon.
