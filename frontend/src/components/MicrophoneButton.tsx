interface Props {
  recording: boolean
  onPress: () => void
  onRelease: () => void
  disabled?: boolean
}

export default function MicrophoneButton({ recording, onPress, onRelease, disabled }: Props) {
  return (
    <button
      onMouseDown={!disabled ? onPress : undefined}
      onMouseUp={!disabled ? onRelease : undefined}
      onTouchStart={!disabled ? onPress : undefined}
      onTouchEnd={!disabled ? onRelease : undefined}
      disabled={disabled}
      className={`w-24 h-24 rounded-full flex items-center justify-center text-4xl shadow-lg transition-all select-none
        ${recording
          ? 'bg-red-500 text-white scale-110 animate-pulse'
          : disabled
            ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
            : 'bg-blue-600 text-white hover:bg-blue-700 active:scale-95'
        }`}
      aria-label={recording ? 'Recording... release to stop' : 'Hold to record'}
    >
      {recording ? '&#9899;' : '&#127908;'}
    </button>
  )
}
