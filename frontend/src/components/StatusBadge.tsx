interface Props {
  status: string
  escalated?: boolean
}

const statusColors: Record<string, string> = {
  in_progress: 'bg-yellow-100 text-yellow-800',
  awaiting_review: 'bg-orange-100 text-orange-800',
  under_review: 'bg-blue-100 text-blue-800',
  completed: 'bg-green-100 text-green-800',
  escalated: 'bg-red-100 text-red-800',
}

export default function StatusBadge({ status, escalated }: Props) {
  const displayStatus = escalated ? 'escalated' : status
  const color = statusColors[displayStatus] || 'bg-gray-100 text-gray-800'

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${color}`}>
      {displayStatus.replace(/_/g, ' ')}
    </span>
  )
}
