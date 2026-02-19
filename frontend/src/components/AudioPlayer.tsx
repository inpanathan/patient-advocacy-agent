interface Props {
  src: string
}

export default function AudioPlayer({ src }: Props) {
  return (
    <audio controls src={src} className="mt-2 w-full h-8" preload="auto">
      Your browser does not support audio playback.
    </audio>
  )
}
