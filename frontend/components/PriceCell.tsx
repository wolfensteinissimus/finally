"use client";
import { useEffect, useRef, useState } from "react";

interface Props {
  price: number | null | undefined;
  testId: string;
  className?: string;
}

/** Shows a price and briefly flashes green/red when it changes. */
export default function PriceCell({ price, testId, className = "" }: Props) {
  const prev = useRef<number | null | undefined>(price);
  const [flash, setFlash] = useState<"" | "flash-up" | "flash-down">("");
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const p = prev.current;
    prev.current = price;
    if (p == null || price == null || p === price) return;
    setFlash(price > p ? "flash-up" : "flash-down");
    setTick((t) => t + 1);
    const id = setTimeout(() => setFlash(""), 500);
    return () => clearTimeout(id);
  }, [price]);

  return (
    <span
      key={tick}
      data-testid={testId}
      data-flash={flash || undefined}
      className={`num inline-block px-1 rounded-sm ${flash} ${className}`}
    >
      {price == null ? "--" : price.toFixed(2)}
    </span>
  );
}
