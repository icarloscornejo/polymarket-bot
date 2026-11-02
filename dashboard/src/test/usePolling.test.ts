import { renderHook } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { usePolling } from '../hooks/usePolling'

describe('usePolling', () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.useRealTimers() })

  it('calls fn immediately on mount', () => {
    const fn = vi.fn()
    renderHook(() => usePolling(fn, 5000))
    expect(fn).toHaveBeenCalledTimes(1)
  })

  it('calls fn again after interval', () => {
    const fn = vi.fn()
    renderHook(() => usePolling(fn, 5000))
    vi.advanceTimersByTime(5000)
    expect(fn).toHaveBeenCalledTimes(2)
  })

  it('clears interval on unmount', () => {
    const fn = vi.fn()
    const { unmount } = renderHook(() => usePolling(fn, 5000))
    unmount()
    vi.advanceTimersByTime(10000)
    expect(fn).toHaveBeenCalledTimes(1)
  })

  it('uses latest fn ref without re-running effect', () => {
    let count = 0
    const { rerender } = renderHook(({ fn }) => usePolling(fn, 5000), {
      initialProps: { fn: () => { count++ } },
    })
    rerender({ fn: () => { count += 10 } })
    vi.advanceTimersByTime(5000)
    expect(count).toBe(11) // 1 from mount + 10 from interval with new fn
  })
})
