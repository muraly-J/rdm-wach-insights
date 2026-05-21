import json

import pandas as pd

# Load data
df = pd.read_csv('cyberview_mqtt_middleware_audit.csv')

# Parse payloads safely
def parse_payload(p):
    try:
        # Handle double escaped quotes if present
        p = p.replace('""', '"')
        return json.loads(p)
    except Exception:
        return {}

df['parsed'] = df['Payload'].apply(parse_payload)

# Extract device path (everything except last two segments: type and metric)
df['device_path'] = df['Topic'].apply(lambda t: '/'.join(t.split('/')[:-2]))
df['device_name'] = df['device_path'].apply(lambda p: p.split('/')[-1])
df['metric_type'] = df['Topic'].apply(lambda t: t.split('/')[-2])
df['metric_name'] = df['Topic'].apply(lambda t: t.split('/')[-1])

# Group by device
devices = df.groupby('device_path')

# Generate markdown report
md = "# 🔍 Cyberview MQTT Device Analysis Report\n\n"
md += f"**Total Devices Analyzed:** {devices.ngroups}\n"
md += f"**Total Records:** {len(df)}\n"
md += f"**Time Window:** {df['Timestamp'].min()} to {df['Timestamp'].max()}\n\n"
md += "---\n\n"

for device_path, group in devices:
    device_name = group['device_name'].iloc[0]
    md += f"## 🖥️ Device: `{device_name}`\n"
    md += f"**Full Path:** `{device_path}`\n"
    md += f"**Total Messages:** {len(group)}\n\n"

    # Metrics summary
    metrics = group.groupby('metric_name').agg(
        count=('Topic', 'size'),
        units=('parsed', lambda x: list(set([p.get('unit', 'N/A') for p in x]))),
        val_types=('parsed', lambda x: list(set([type(p.get('val')).__name__ for p in x if 'val' in p]))),
        examples=('Payload', lambda x: x.head(2).tolist())
    ).reset_index()

    md += "### 📊 Metrics Overview\n"
    md += "| Metric | Count | Units | Value Types | Example Payloads |\n"
    md += "|--------|-------|-------|-------------|------------------|\n"
    for _, row in metrics.iterrows():
        md += f"| {row['metric_name']} | {row['count']} | {', '.join(row['units'])} | {', '.join(row['val_types'])} | `{str(row['examples'])[:60]}...` |\n"
    md += "\n"

    # Value statistics for numeric metrics
    numeric_mask = group['parsed'].apply(lambda x: isinstance(x.get('val'), (int, float)))
    numeric_group = group[numeric_mask]

    if not numeric_group.empty:
        md += "### 📈 Numeric Value Statistics\n"
        stats_data = []
        for metric, m_group in numeric_group.groupby('metric_name'):
            vals = [p.get('val', 0) for p in m_group['parsed']]
            stats_data.append({
                'Metric': metric,
                'Min': min(vals),
                'Max': max(vals),
                'Mean': sum(vals) / len(vals),
                'Std Dev': (sum([(v - (sum(vals)/len(vals)))**2 for v in vals]) / len(vals))**0.5
            })
        stats_df = pd.DataFrame(stats_data)

        # Custom markdown table formatter (avoids tabulate dependency)
        md += "| Metric | Min | Max | Mean | Std Dev |\n"
        md += "|--------|-----|-----|------|---------|\n"
        for _, row in stats_df.iterrows():
            md += f"| {row['Metric']} | {row['Min']:.2f} | {row['Max']:.2f} | {row['Mean']:.2f} | {row['Std Dev']:.2f} |\n"
        md += "\n"

    md += "---\n\n"

# Save report
output_path = 'device_analysis_report.md'
with open(output_path, 'w') as f:
    f.write(md)

print(f"✅ Report generated successfully: {output_path}")
print(f"📄 Total devices documented: {devices.ngroups}")
