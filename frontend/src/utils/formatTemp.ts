export const formatTemp = (temp: number | null): string =>
  temp === null ? '—' : `${temp.toFixed(1)}°C`
