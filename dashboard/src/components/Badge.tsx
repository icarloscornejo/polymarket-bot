import { clsx } from 'clsx'

interface BadgeProps {
  color: 'green' | 'yellow' | 'red' | 'gray' | 'blue'
  children: React.ReactNode
}

const colorMap: Record<BadgeProps['color'], string> = {
  green: 'bg-green-900/50 text-green-400 border border-green-700',
  yellow: 'bg-yellow-900/50 text-yellow-400 border border-yellow-700',
  red: 'bg-red-900/50 text-red-400 border border-red-700',
  gray: 'bg-gray-800 text-gray-400 border border-gray-700',
  blue: 'bg-blue-900/50 text-blue-400 border border-blue-700',
}

export function Badge({ color, children }: BadgeProps) {
  return (
    <span className={clsx('inline-flex items-center px-2 py-0.5 rounded text-xs font-medium', colorMap[color])}>
      {children}
    </span>
  )
}
