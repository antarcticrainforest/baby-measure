from pathlib import Path
import re
from setuptools import setup, find_packages
from typing import List


def get_assests(*parts: str) -> List[str]:
    asset_dir = Path(__file__).parent.joinpath(*parts)
    out = [str(d.relative_to(asset_dir.parent)) for d in asset_dir.rglob("*")]
    return out


meta = dict(
    description="Add baby mesurements",
    url="https://github.com/antarcticrainforest/geojson-viewer",
    author="Martin Bergemann",
    author_email="martin.bergemann@posteo.org",
    include_package_data=True,
    long_description_content_type="text/markdown",
    license="BSD-3-Clause",
    python_requires=">=3.7",
    package_data={"": get_assests("src", "baby_measure", "assets")},
    project_urls={
        "Issues": "https://github.com/antarcticrainforest/geojson-viewer/issues",
        "Source": "https://github.com/antarcticrainforest/geojson-viewer",
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: BSD License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    version="0.1.0",  # find_version("src", "geojson_viewer", "app.py"),
    package_dir={"": "src"},
    entry_points={"console_scripts": ["baby-measure = baby_measure.app:cli"]},
    install_requires=[
        "dash",
        "dash-datetimepicker",
        "dash-loading-spinners",
        "sqlalchemy",
        "pymysql",
        "gunicorn",
        "pandas",
    ],
    extras_require={
        "tests": [
            "black",
            "flake8",
            "mypy",
        ],
        "jupyter": [
            "jupyter",
            "jupyterlab",
            "jupyter-dash",
        ],
    },
)

setup(name="baby_measure", packages=find_packages("src"), **meta)
