interface Props {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
}

export default function Sparkline({ data, width = 72, height = 22, color }: Props) {
  if (data.length < 2) {
    return <svg width={width} height={height} aria-hidden="true" data-testid="sparkline-empty" />;
  }
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const pts = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * (width - 2) + 1;
      const y = height - 2 - ((v - min) / range) * (height - 4);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  const stroke = color ?? (data[data.length - 1] >= data[0] ? "#26d07c" : "#ff5470");
  return (
    <svg width={width} height={height} aria-hidden="true" data-testid="sparkline">
      <polyline points={pts} fill="none" stroke={stroke} strokeWidth="1.3" strokeLinejoin="round" />
    </svg>
  );
}
