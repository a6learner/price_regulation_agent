interface Props {
  sender: 'user' | 'ai'
  content: string
}

export default function MessageBubble({ sender, content }: Props) {
  if (sender === 'user') {
    return (
      <div className="flex justify-end">
        <div className="bg-surface-container-high text-on-surface p-4 rounded-xl rounded-tr-sm max-w-2xl text-sm leading-relaxed shadow-sm">
          {content}
        </div>
      </div>
    )
  }

  return null // AI messages are rendered via EvidenceCard
}
