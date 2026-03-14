"use client"

import { Agent } from "@/types/agent"
import { AgentCard } from "./AgentCard"

interface Props {
  agents: Agent[]
  onAgentClick: (agentId: string) => void
}

export function AgentGrid({ agents, onAgentClick }: Props) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium text-neutral-400 uppercase tracking-wider">
          Agents
        </span>
        <span className="text-xs text-neutral-300">{agents.length}</span>
      </div>
      <div className="grid grid-cols-3 gap-3">
        {agents.map((agent) => (
          <AgentCard
            key={agent.id}
            agent={agent}
            onClick={() => onAgentClick(agent.id)}
          />
        ))}
        {agents.length === 0 &&
          Array.from({ length: 9 }).map((_, i) => (
            <div key={i} className="h-28 rounded-lg bg-neutral-50 border border-neutral-200 animate-pulse" />
          ))
        }
      </div>
    </div>
  )
}
