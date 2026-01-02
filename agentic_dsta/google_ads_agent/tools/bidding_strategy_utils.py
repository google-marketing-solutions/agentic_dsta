# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Utilities for Google Ads bidding strategy validation and mappings."""

from typing import Any, Dict, List, Optional
import logging


logger = logging.getLogger(__name__)

# Example structure for allowed strategies by channel type
ALLOWED_STRATEGIES = {
    "PERFORMANCE_MAX": [
        "MAXIMIZE_CONVERSIONS",
        "MAXIMIZE_CONVERSION_VALUE",
    ],
    "SEARCH": [
        "MANUAL_CPC",
        "TARGET_SPEND",
        "MAXIMIZE_CONVERSIONS",
        "MAXIMIZE_CONVERSION_VALUE",
        "TARGET_IMPRESSION_SHARE",
    ],
    "DISPLAY": [
        "MANUAL_CPC",
        "MANUAL_CPM",
        "TARGET_CPM",
        "MAXIMIZE_CONVERSIONS",
        "MAXIMIZE_CONVERSION_VALUE",
    ],
    "VIDEO": [
        "MANUAL_CPV",
        "TARGET_CPV",
        "TARGET_CPM",
        "MAXIMIZE_CONVERSIONS", # For Video Action Campaigns
    ],
    "HOTEL": [
        "MANUAL_CPC",
        "PERCENT_CPC",
        "COMMISSION",
    ],
}

PROHIBITED_STRATEGIES = {
    "PERFORMANCE_MAX": [
        "MANUAL_CPC", "TARGET_IMPRESSION_SHARE", "TARGET_SPEND", "MANUAL_CPM",
        "MANUAL_CPV", "PERCENT_CPC", "COMMISSION"
    ],
    "SEARCH": ["MANUAL_CPM", "COMMISSION", "MANUAL_CPV", "PERCENT_CPC"],
    "DISPLAY": ["TARGET_IMPRESSION_SHARE", "COMMISSION", "MANUAL_CPV", "PERCENT_CPC"],
    "VIDEO": [
        "MANUAL_CPC", "TARGET_IMPRESSION_SHARE", "MAXIMIZE_CONVERSION_VALUE",
        "TARGET_ROAS", "TARGET_SPEND", "PERCENT_CPC", "COMMISSION"
    ],
    "HOTEL": [
        "TARGET_IMPRESSION_SHARE", "MANUAL_CPM", "TARGET_CPM",
        "MAXIMIZE_CONVERSIONS", "MAXIMIZE_CONVERSION_VALUE",
        "TARGET_CPA", "TARGET_ROAS", "TARGET_SPEND", "MANUAL_CPV"
    ],
}

def validate_strategy_change(channel_type: str, target_strategy: str) -> bool:
    """Validates if the target strategy is allowed for the given channel type."""
    channel_type = channel_type.upper()
    target_strategy = target_strategy.upper()
    if channel_type not in ALLOWED_STRATEGIES:
        logger.warning(
            "Unknown channel type '%s'",
            channel_type,
            extra={'channel_type': channel_type}
        )
        return False # Fail safe
    if target_strategy not in ALLOWED_STRATEGIES[channel_type]:
        return False
    if (channel_type in PROHIBITED_STRATEGIES and
            target_strategy in PROHIBITED_STRATEGIES[channel_type]):
        # This case should ideally be caught by the ALLOWED_STRATEGIES check,
        # but this adds an extra layer of safety based on the markdown's prohibited list.
        return False
    return True

