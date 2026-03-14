import { CATEGORY_LABELS } from "@/lib/constants"

interface Props {
  category: string
  size?: "sm" | "md"
}

export function CategoryBadge({ category, size = "sm" }: Props) {
  const label = CATEGORY_LABELS[category] ?? category
  const px = size === "sm" ? "px-1.5 py-0.5 text-xs" : "px-2 py-1 text-sm"

  return (
    <span className={`inline-flex items-center rounded border border-neutral-200 bg-neutral-50 text-neutral-500 ${px}`}>
      {label}
    </span>
  )
}
