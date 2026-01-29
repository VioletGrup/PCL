#!/usr/bin/env python3
"""
Pytest configuration and shared fixtures
"""

from __future__ import annotations

import pytest

from ProjectConstraints import ProjectConstraints


@pytest.fixture
def standard_constraints():
    """Standard project constraints matching actual project values"""
    return ProjectConstraints(
        min_reveal_height=1.375,
        max_reveal_height=1.675,
        pile_install_tolerance=0.0,
        max_incline=0.15,
        target_height_percentage=0.5,
        max_angle_rotation=0.0,
        edge_overhang=0.0,
    )


@pytest.fixture
def constraints_with_tolerance():
    """Constraints with installation tolerance"""
    return ProjectConstraints(
        min_reveal_height=1.375,
        max_reveal_height=1.675,
        pile_install_tolerance=0.1,
        max_incline=0.15,
        target_height_percentage=0.5,
        max_angle_rotation=0.0,
        edge_overhang=0.0,
    )
