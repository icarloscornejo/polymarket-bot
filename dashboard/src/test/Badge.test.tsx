import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { Badge } from '../components/Badge'

describe('Badge', () => {
  it('renders children text', () => {
    render(<Badge color="green">LIVE</Badge>)
    expect(screen.getByText('LIVE')).toBeInTheDocument()
  })
  it('renders each color variant without error', () => {
    const colors = ['green', 'yellow', 'red', 'gray', 'blue'] as const
    colors.forEach((color) => {
      const { unmount } = render(<Badge color={color}>{color}</Badge>)
      expect(screen.getByText(color)).toBeInTheDocument()
      unmount()
    })
  })
})
