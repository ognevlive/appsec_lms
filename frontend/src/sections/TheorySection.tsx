import Icon from '../components/Icon';
import { Md } from '../components/Md';

interface TheorySectionProps {
  content: string;
}

export default function TheorySection({ content }: TheorySectionProps) {
  return (
    <section className="bg-surface-container-low p-8">
      <h3 className="text-xs font-bold uppercase tracking-[0.3em] text-primary mb-6 flex items-center gap-2">
        <Icon name="menu_book" size="sm" />
        Теоретический материал
      </h3>
      <Md>{content}</Md>
    </section>
  );
}
