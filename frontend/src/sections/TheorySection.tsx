import Icon from '../components/Icon';
import { Md } from '../components/Md';

interface TheorySectionProps {
  config: Record<string, any> | undefined;
}

function extractYoutubeId(src: string): string {
  if (src.includes('youtube.com') || src.includes('youtu.be')) {
    try {
      const url = new URL(src);
      const v = url.searchParams.get('v');
      if (v) return v;
      return url.pathname.split('/').filter(Boolean).pop() || src;
    } catch {
      return src.split('/').pop() || src;
    }
  }
  return src;
}

export default function TheorySection({ config }: TheorySectionProps) {
  const contentKind = (config?.content_kind as string | undefined) ?? 'text';
  const content = (config?.content as string | undefined) ?? '';
  const video = config?.video as { provider?: string; src?: string } | undefined;

  const showVideo = contentKind === 'video' || contentKind === 'mixed';
  const showText = contentKind === 'text' || contentKind === 'mixed';

  return (
    <section className="bg-surface-container-low p-8">
      <h3 className="text-xs font-bold uppercase tracking-[0.3em] text-primary mb-6 flex items-center gap-2">
        <Icon name="menu_book" size="sm" />
        Теоретический материал
      </h3>

      {showVideo && video?.src && video.provider === 'youtube' && (
        <div className="aspect-video bg-black mb-6">
          <iframe
            className="w-full h-full"
            src={`https://www.youtube.com/embed/${extractYoutubeId(video.src)}`}
            title="video"
            allowFullScreen
          />
        </div>
      )}

      {showVideo && video?.src && video.provider !== 'youtube' && (
        <video controls className="w-full mb-6 bg-black" src={video.src} />
      )}

      {showText && <Md>{content}</Md>}
    </section>
  );
}
