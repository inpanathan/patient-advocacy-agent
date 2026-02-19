import { useEffect, useState } from 'react'
import api from '../lib/api'

interface Props {
  caseId: string
  imageId: string
}

export default function CaseImage({ caseId, imageId }: Props) {
  const [src, setSrc] = useState<string | null>(null)

  useEffect(() => {
    let url: string | null = null
    api
      .get(`/cases/${caseId}/images/${imageId}`, { responseType: 'blob' })
      .then((res) => {
        url = URL.createObjectURL(res.data)
        setSrc(url)
      })
      .catch(() => {})

    return () => {
      if (url) URL.revokeObjectURL(url)
    }
  }, [caseId, imageId])

  if (!src) return <div className="p-4 border rounded-lg text-sm text-gray-400 text-center">Loading image...</div>

  return (
    <div className="border rounded-lg overflow-hidden">
      <img src={src} alt="Case photo" className="w-full h-auto" />
    </div>
  )
}
