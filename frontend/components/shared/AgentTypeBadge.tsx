import { AGENT_TYPE_LABELS } from "@/lib/constants"

interface Props {
  type: string
}

export function AgentTypeBadge({ type }: Props) {
  const label = AGENT_TYPE_LABELS[type] ?? type

  return (
    <span className="inline-flex items-center rounded border border-neutral-200 bg-neutral-50 px-1.5 py-0.5 text-xs text-neutral-500">
      {label}
    </span>
  )
}
