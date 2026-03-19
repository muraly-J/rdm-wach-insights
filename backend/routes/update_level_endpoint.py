#!/usr/bin/env python3
"""Update the level endpoint to pass devices_filter parameter."""

with open('/Users/rdmasia/wach-insight/backend/routes/electrical_risk.py', 'r') as f:
    content = f.read()

# Replace the section
old_lines = """        # Run assessment for this level
        result = await get_electrical_risk_check(
            time_range=time_range,
            cluster_by_level=True
        )

        # Filter assessments to only include devices from this level
        assessments = result.get("assessments", [])
        level_assessments = [a for a in assessments if a.get("level") == f"Level {level}"]"""

new_lines = """        # Run assessment for this level with device filter (only process devices for this level)
        result = await get_electrical_risk_check(
            time_range=time_range,
            cluster_by_level=True,
            devices_filter=level_devices
        )

        # Get assessments from result (they're already filtered by level)
        assessments = result.get("assessments", [])"""

content = content.replace(old_lines, new_lines)

with open('/Users/rdmasia/wach-insight/backend/routes/electrical_risk.py', 'w') as f:
    f.write(content)

print("Updated successfully")
