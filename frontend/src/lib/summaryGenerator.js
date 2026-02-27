/**
 * summaryGenerator.js
 * ====================
 * Auto-generate contextual summaries for dashboard charts
 * based on actual CSV data (no LLM API calls).
 *
 * Usage:
 *   import { buildSummary, buildWorstDevicesList } from '../lib/summaryGenerator'
 *
 *   const summary = buildSummary(
 *     'health_index',
 *     wideData,
 *     ahuIds,
 *     highlightedAhu,  // null or ahu_id
 *     timeRange        // '24h', '7d', '30d'
 *   )
 */

// Threshold definitions per metric
const THRESHOLDS = {
  health_index: [
    { value: 80, label: 'Healthy', direction: 'up' },
    { value: 60, label: 'Monitor', direction: 'up' },
    { value: 40, label: 'Maintenance Soon', direction: 'up' },
  ],
  energy_anomaly: [
    { value: 0.6, label: 'High', direction: 'down' },
    { value: 0.3, label: 'Elev.', direction: 'down' },
  ],
  pf_degradation: [
    { value: 0.6, label: 'High', direction: 'down' },
    { value: 0.3, label: 'Elev.', direction: 'down' },
  ],
  phase_imbalance: [
    { value: 0.6, label: 'High', direction: 'down' },
    { value: 0.3, label: 'Elev.', direction: 'down' },
  ],
  thd_drift: [
    { value: 0.6, label: 'High', direction: 'down' },
    { value: 0.3, label: 'Elev.', direction: 'down' },
  ],
  overload: [
    { value: 0.6, label: 'High', direction: 'down' },
    { value: 0.3, label: 'Elev.', direction: 'down' },
  ],
};

// Metric-specific labels
const METRIC_LABELS = {
  health_index: 'Health Index',
  energy_anomaly: 'Energy Anomaly',
  pf_degradation: 'PF Degradation',
  phase_imbalance: 'Phase Imbalance',
  thd_drift: 'THD Drift',
  overload: 'Overload',
};

/**
 * Format date based on time range
 */
function formatDate(dateStr, timeRange) {
  const date = new Date(dateStr);
  
  if (timeRange === '24h') {
    return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
  } else if (timeRange === '7d') {
    const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    return `${days[date.getDay()]} ${date.getDate()}`;
  } else {
    // 30d
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return `${date.getDate()} ${months[date.getMonth()]}`;
  }
}

/**
 * Calculate slope (trend) over data series
 */
function calculateSlope(data, metricKey) {
  if (!data || data.length < 2) return 0;
  
  // Extract values for the metric
  const values = data.map(row => {
    if (row.ahu_id) {
      // Long format: single column for all AHUs
      return parseFloat(row[metricKey] || 0);
    } else {
      // Wide format: multiple columns
      return parseFloat(row[metricKey] || 0);
    }
  });
  
  if (values.length < 2) return 0;
  
  // Simple linear regression slope
  const n = values.length;
  const x = Array.from({ length: n }, (_, i) => i);
  const y = values;
  
  const sumX = x.reduce((a, b) => a + b, 0);
  const sumY = y.reduce((a, b) => a + b, 0);
  const sumXY = x.reduce((sum, xi, i) => sum + xi * y[i], 0);
  const sumX2 = x.reduce((sum, xi) => sum + xi * xi, 0);
  
  const denominator = n * sumX2 - sumX * sumX;
  if (denominator === 0) return 0;
  
  const slope = (n * sumXY - sumX * sumY) / denominator;
  return slope;
}

/**
 * Check if a value is above/below threshold
 */
function isAboveThreshold(value, thresholdValue) {
  // For health_index: higher = better
  // For component scores: lower = better (0 is best)
  
  return value >= thresholdValue;
}

/**
 * Get trend direction
 */
function getTrend(slope, isReversed = false) {
  if (slope > 0.01) return { direction: 'rising', icon: '▲' };
  if (slope < -0.01) return { direction: 'falling', icon: '▼' };
  return { direction: 'stable', icon: '' };
}

/**
 * Build summary text for a chart
 */
export function buildSummary(metricKey, data, ahuIds, highlightedAhu, timeRange) {
  if (!data || data.length === 0 || !ahuIds || ahuIds.length === 0) {
    return 'No data available';
  }
  
  const metricLabel = METRIC_LABELS[metricKey] || metricKey;
  const isHealthIndex = metricKey === 'health_index';
  
  // Sort data by timestamp to get chronological order
  const sortedData = [...data].sort((a, b) => {
    return new Date(a.timestamp) - new Date(b.timestamp);
  });
  
  // Get latest row(s)
  const latestTimestamp = sortedData[sortedData.length - 1]?.timestamp;
  const latestRows = sortedData.filter(row => row.timestamp === latestTimestamp);
  
  // Get first row(s) for comparison
  const firstRows = sortedData.filter(row => row.timestamp === sortedData[0].timestamp);
  
  // Filter rows based on highlightedAhu
  let displayRows;
  if (highlightedAhu) {
    // Single device mode: only show data for that AHU
    displayRows = sortedData.filter(row => row.ahu_id === highlightedAhu);
  } else {
    // All devices mode: show all rows
    displayRows = sortedData;
  }
  
  if (displayRows.length === 0) {
    return 'No data available';
  }
  
  // Calculate statistics
  const values = displayRows.map(row => {
    if (row.ahu_id) {
      return parseFloat(row[metricKey] || 0);
    } else {
      return parseFloat(row[metricKey] || 0);
    }
  }).filter(v => !isNaN(v));
  
  if (values.length === 0) {
    return 'No data available';
  }
  
  const currentValue = values[values.length - 1];
  const averageValue = values.reduce((a, b) => a + b, 0) / values.length;
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  
  // Calculate trend
  const slope = calculateSlope(sortedData, metricKey);
  const trend = getTrend(slope, !isHealthIndex);
  
  // Build summary based on mode
  if (highlightedAhu) {
    // Single device focused
    return buildDeviceSummary(highlightedAhu, metricLabel, currentValue, averageValue, minValue, maxValue, trend, timeRange);
  } else {
    // All devices visible
    return buildFleetSummary(metricLabel, sortedData, ahuIds, isHealthIndex, timeRange);
  }
}

/**
 * Build summary for single device
 */
function buildDeviceSummary(ahuId, metricLabel, currentValue, averageValue, minValue, maxValue, trend, timeRange) {
  const lines = [];
  
  // Line 1: Device and metric
  lines.push(`${ahuId} · ${metricLabel} · ${timeRange}`);
  
  // Line 2: Current value and trend
  if (metricLabel === 'Health Index') {
    lines.push(`Latest: ${currentValue.toFixed(1)} (Average: ${averageValue.toFixed(1)})`);
  } else {
    lines.push(`Latest: ${currentValue.toFixed(3)} (Average: ${averageValue.toFixed(3)})`);
  }
  
  // Line 3: Trend and range
  if (trend.direction === 'stable') {
    lines.push('Trending stable');
  } else {
    const directionText = trend.direction === 'rising' ? 'Rising' : 'Falling';
    lines.push(`${directionText} — ${trend.icon} from ${minValue.toFixed(3)} to ${maxValue.toFixed(3)}`);
  }
  
  return lines.join('<br/>');
}

/**
 * Build summary for fleet (all devices)
 */
function buildFleetSummary(metricLabel, data, ahuIds, isHealthIndex, timeRange) {
  // Get latest timestamp
  const sortedData = [...data].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
  const latestTimestamp = sortedData[sortedData.length - 1]?.timestamp;
  
  // Get all values at latest timestamp
  const latestRows = sortedData.filter(row => row.timestamp === latestTimestamp);
  
  // Extract values for all AHUs
  const valuesByAhu = {};
  latestRows.forEach(row => {
    if (row.ahu_id) {
      const val = parseFloat(row[metricLabel === 'Health Index' ? 'health_index' : metricLabel] || 0);
      valuesByAhu[row.ahu_id] = val;
    } else {
      // Wide format
      ahuIds.forEach(ahuId => {
        if (row[ahuId] !== undefined) {
          valuesByAhu[ahuId] = parseFloat(row[ahuId]);
        }
      });
    }
  });
  
  // Count by tier (for health_index)
  if (isHealthIndex) {
    let healthy = 0, monitor = 0, maintenanceSoon = 0, critical = 0;
    Object.values(valuesByAhu).forEach(val => {
      if (val >= 80) healthy++;
      else if (val >= 60) monitor++;
      else if (val >= 40) maintenanceSoon++;
      else critical++;
    });
    
    const bestAhu = Object.entries(valuesByAhu).sort((a, b) => b[1] - a[1])[0];
    const worstAhu = Object.entries(valuesByAhu).sort((a, b) => a[1] - b[1])[0];
    
    const lines = [];
    lines.push(`${ahuIds.length} AHUs on Level 1 · latest snapshot`);
    lines.push(`${healthy} Healthy, ${monitor} Monitor, ${maintenanceSoon} Maintenance Soon, ${critical} Critical`);
    if (bestAhu && worstAhu) {
      lines.push(`Best: ${bestAhu[0]} (${bestAhu[1].toFixed(1)}). Worst: ${worstAhu[0]} (${worstAhu[1].toFixed(1)})`);
    }
    
    // Check trend
    if (sortedData.length >= 2) {
      const firstTimestamp = sortedData[0].timestamp;
      const firstRows = sortedData.filter(row => row.timestamp === firstTimestamp);
      const firstAvg = firstRows.reduce((sum, row) => sum + (parseFloat(row.health_index) || 0), 0) / firstRows.length;
      const latestAvg = latestRows.reduce((sum, row) => sum + (parseFloat(row.health_index) || 0), 0) / latestRows.length;
      
      const diff = latestAvg - firstAvg;
      if (Math.abs(diff) < 1) {
        lines.push('Fleet average trending stable');
      } else if (diff > 0) {
        lines.push(`Fleet average improving by ${diff.toFixed(1)} points`);
      } else {
        lines.push(`Fleet average declining by ${Math.abs(diff).toFixed(1)} points`);
      }
    }
    
    return lines.join('<br/>');
  } else {
    // Component score summary
    const thresholds = THRESHOLDS[metricLabel] || [];
    const highThreshold = thresholds.find(t => t.label === 'High')?.value ?? 0.6;
    const elevThreshold = thresholds.find(t => t.label === 'Elev.')?.value ?? 0.3;
    
    // Count devices above thresholds
    const highCount = Object.values(valuesByAhu).filter(val => val >= highThreshold).length;
    const elevCount = Object.values(valuesByAhu).filter(val => val >= elevThreshold && val < highThreshold).length;
    const normalCount = Object.values(valuesByAhu).filter(val => val < elevThreshold).length;
    
    // Find worst devices (highest scores for component metrics)
    const sortedByValue = Object.entries(valuesByAhu).sort((a, b) => b[1] - a[1]);
    const worstDevices = sortedByValue.filter((_, i) => i < 3).map(([id, val]) => `${id} (${val.toFixed(2)})`).join(', ');
    
    const lines = [];
    lines.push(`${metricLabel} · ${timeRange} · all devices`);
    lines.push(`${normalCount} normal, ${elevCount} elevated, ${highCount} high`);
    if (worstDevices) {
      lines.push(`Worst: ${worstDevices}`);
    }
    
    // Check trend
    if (sortedData.length >= 2 && ahuIds.length > 0) {
      const firstTimestamp = sortedData[0].timestamp;
      const firstRows = sortedData.filter(row => row.timestamp === firstTimestamp);
      
      // Calculate average for this metric at start
      let firstSum = 0, firstCount = 0;
      firstRows.forEach(row => {
        if (row[metricLabel] !== undefined) {
          firstSum += parseFloat(row[metricLabel]);
          firstCount++;
        }
      });
      
      // Calculate average for this metric at end
      let lastSum = 0, lastCount = 0;
      latestRows.forEach(row => {
        if (row[metricLabel] !== undefined) {
          lastSum += parseFloat(row[metricLabel]);
          lastCount++;
        }
      });
      
      if (firstCount > 0 && lastCount > 0) {
        const firstAvg = firstSum / firstCount;
        const lastAvg = lastSum / lastCount;
        const diff = lastAvg - firstAvg;
        
        if (Math.abs(diff) < 0.01) {
          lines.push('Average trending stable');
        } else if (diff > 0) {
          lines.push(`Average rising by ${diff.toFixed(3)}`);
        } else {
          lines.push(`Average declining by ${Math.abs(diff).toFixed(3)}`);
        }
      }
    }
    
    return lines.join('<br/>');
  }
}

/**
 * Get tier name and color for a given value
 */
function getTierInfo(metricKey, value) {
  const isHealthIndex = metricKey === 'health_index';

  if (isHealthIndex) {
    // Health Index: 0-100 scale
    if (value < 40) return { tier: 'Critical', color: '#ff4d6d', label: 'Critical (0-39)' };
    if (value < 60) return { tier: 'MaintenanceSoon', color: '#f5734e', label: 'Maintenance Soon (40-59)' };
    if (value < 80) return { tier: 'Monitor', color: '#f5a623', label: 'Monitor (60-79)' };
    return { tier: 'Healthy', color: '#00c9b1', label: 'Healthy (80-100)' };
  } else {
    // Component metrics: use threshold values
    if (value >= 0.6) return { tier: 'High', color: '#ff4d6d', label: 'High (≥0.6)' };
    if (value >= 0.3) return { tier: 'Elevated', color: '#f5a623', label: 'Elevated (0.3-0.6)' };
    return { tier: 'Normal', color: '#00c9b1', label: 'Normal (<0.3)' };
  }
}

/**
 * Build list of worst devices (right panel - broad mode)
 */
export function buildWorstDevicesList(metricKey, data, ahuIds) {
  if (!data || data.length === 0 || !ahuIds || ahuIds.length === 0) {
    return { label: 'Latest', devicesByTier: {}, allDevices: [] };
  }

  // Get latest timestamp
  const sortedData = [...data].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
  const latestTimestamp = sortedData[sortedData.length - 1]?.timestamp;
  const latestRows = sortedData.filter(row => row.timestamp === latestTimestamp);

  // Extract values at latest timestamp
  const valuesByAhu = {};
  latestRows.forEach(row => {
    if (row.ahu_id) {
      const val = parseFloat(row[metricKey] || 0);
      valuesByAhu[row.ahu_id] = val;
    } else if (row[metricKey] !== undefined) {
      valuesByAhu[row[ahuIds[0]]] = parseFloat(row[metricKey]);
    }
  });

  // Filter to only devices we have data for
  const validDevices = ahuIds.filter(id => valuesByAhu[id] !== undefined);

  if (validDevices.length === 0) {
    return { label: 'Latest', devicesByTier: {}, allDevices: [] };
  }

  // Group devices by tier
  const devicesByTier = {};
  const allDevices = [];

  validDevices.forEach(ahuId => {
    const value = valuesByAhu[ahuId];
    const tierInfo = getTierInfo(metricKey, value);

    if (!devicesByTier[tierInfo.tier]) {
      devicesByTier[tierInfo.tier] = [];
    }
    devicesByTier[tierInfo.tier].push({ ahuId, value });

    allDevices.push({
      ahuId,
      value,
      tier: tierInfo.tier,
      tierLabel: tierInfo.label,
      tierColor: tierInfo.color
    });
  });

  // Sort devices within each tier by value (descending for components, ascending for health index)
  const isHealthIndex = metricKey === 'health_index';
  Object.keys(devicesByTier).forEach(tier => {
    devicesByTier[tier].sort((a, b) => {
      if (isHealthIndex) {
        return a.value - b.value; // Ascending for health index
      } else {
        return b.value - a.value; // Descending for components
      }
    });
  });

  return { label: 'Latest', devicesByTier, allDevices };
}

/**
 * Build threshold event log (right panel - focused mode)
 */
export function buildThresholdEvents(metricKey, data, ahuId) {
  if (!data || data.length === 0) {
    return { label: `Threshold Events · ${ahuId}`, events: [] };
  }
  
  const thresholds = THRESHOLDS[metricKey] || [];
  if (thresholds.length === 0) {
    return { label: `Threshold Events · ${ahuId}`, events: [] };
  }
  
  // Get data for this AHU
  const ahuData = data.filter(row => row.ahu_id === ahuId);
  
  if (ahuData.length < 2) {
    return { label: `Threshold Events · ${ahuId}`, events: [{ date: '-', type: 'info', message: 'Insufficient data for threshold analysis' }] };
  }
  
  // Sort by timestamp
  const sortedData = [...ahuData].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
  
  // Detect crossings
  const events = [];
  for (let i = 1; i < sortedData.length; i++) {
    const prevRow = sortedData[i - 1];
    const currRow = sortedData[i];
    
    const prevVal = parseFloat(prevRow[metricKey] || 0);
    const currVal = parseFloat(currRow[metricKey] || 0);
    
    if (isNaN(prevVal) || isNaN(currVal)) continue;
    
    thresholds.forEach(threshold => {
      const crossedUp = prevVal < threshold.value && currVal >= threshold.value;
      const crossedDown = prevVal >= threshold.value && currVal < threshold.value;
      
      if (crossedUp) {
        events.push({
          date: formatDate(prevRow.timestamp, '7d'),
          type: 'improving',
          message: `recovered above ${threshold.value}`,
        });
      } else if (crossedDown) {
        events.push({
          date: formatDate(prevRow.timestamp, '7d'),
          type: 'worsening',
          message: `dropped below ${threshold.value}`,
        });
      }
    });
  }
  
  // Limit events
  const maxEvents = 8;
  const limitedEvents = events.slice(0, maxEvents);
  
  if (events.length > maxEvents) {
    limitedEvents.push({
      date: '+ more',
      type: 'info',
      message: `+${events.length - maxEvents} more events`,
    });
  }
  
  return { label: `Threshold Events · ${ahuId}`, events: limitedEvents };
}

export default {
  buildSummary,
  buildWorstDevicesList,
  buildThresholdEvents,
};
