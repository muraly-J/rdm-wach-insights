export interface DeviceInfo {
  id: string;
  label: string;
  department: string;
  area: string;
}

export function resolveDeviceLabel(id: string, devices: DeviceInfo[]): string {
  const device = devices.find((d) => d.id === id);
  if (!device) return id;
  return device.label && device.department
    ? `${device.label} \u2014 ${device.department}`
    : device.label || id;
}

export function buildLabelMap(devices: DeviceInfo[]): Record<string, string> {
  const map: Record<string, string> = {};
  for (const d of devices) {
    map[d.id] = resolveDeviceLabel(d.id, devices);
  }
  return map;
}
