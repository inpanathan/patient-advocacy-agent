import { useCallback } from 'react'

interface Props {
  recording: boolean
  onPress: () => void
  onRelease: () => void
  disabled?: boolean
}

export default function MicrophoneButton({ recording, onPress, onRelease, disabled }: Props) {
  // Use onPointerDown/Up to unify touch and mouse — avoids the
  // double-fire problem where both onTouchStart+onMouseDown trigger.
  const handlePointerDown = useCallback(
    (e: React.PointerEvent) => {
      if (disabled) return
      // Capture the pointer so pointerup fires even if finger moves off button
      ;(e.target as HTMLElement).setPointerCapture(e.pointerId)
      onPress()
    },
    [disabled, onPress],
  )

  const handlePointerUp = useCallback(
    (e: React.PointerEvent) => {
      if (disabled) return
      ;(e.target as HTMLElement).releasePointerCapture(e.pointerId)
      onRelease()
    },
    [disabled, onRelease],
  )

  return (
    <button
      onPointerDown={handlePointerDown}
      onPointerUp={handlePointerUp}
      disabled={disabled}
      className={`w-24 h-24 rounded-full flex items-center justify-center text-4xl shadow-lg transition-all select-none touch-none
        ${recording
          ? 'bg-red-500 text-white scale-110 animate-pulse'
          : disabled
            ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
            : 'bg-blue-600 text-white hover:bg-blue-700 active:scale-95'
        }`}
      aria-label={recording ? 'Recording... release to stop' : 'Hold to record'}
    >
      {recording ? '\u26AB' : '\uD83C\uDFA4'}
    </button>
  )
}
