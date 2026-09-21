import { useEffect, useState } from 'react';
import type { AugmentDef } from '@reforged/schema';
import { api } from '../../services/api.js';
import { AugmentCard } from './AugmentCard.js';

interface Props {
  runId: string;
  onPick: (augmentId: string) => void;
}

export function AugmentPicker({ runId, onPick }: Props) {
  const [offers, setOffers] = useState<AugmentDef[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.getAugmentOffers(runId).then((result) => {
      if (!cancelled) setOffers(result);
    });
    return () => {
      cancelled = true;
    };
  }, [runId]);

  return (
    <div className="modal-backdrop">
      <div className="augment-picker">
        <h2>Wybierz trwały bonus</h2>
        {!offers && <p>Ładowanie...</p>}
        <div className="augment-offers">
          {offers?.map((augment) => (
            <AugmentCard key={augment.id} augment={augment} onPick={() => onPick(augment.id)} />
          ))}
        </div>
      </div>
    </div>
  );
}
