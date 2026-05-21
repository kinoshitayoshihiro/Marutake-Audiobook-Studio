# Channel Report Types

```ts
type VideoReport = {
  videoId: string;
  title: string;
  description?: string;
  author?: string;
  series?: string;
  publishedAt?: string;
  views: number;
  estimatedMinutesWatched: number;
  averageViewDuration: number;
  impressions?: number;
  impressionCtr?: number;
  durationSeconds?: number;
  isShortCandidate: boolean;
  isPublic: boolean;
  isUnlisted: boolean;
  isPrivate: boolean;
  contentTypeBucket?: string;
  hasDescriptionSynopsis: boolean;
  hasDescriptionCharacters: boolean;
  hasDescriptionGlossary: boolean;
  diagnosisTags: string[];
  recommendedActions: string[];
  anthologySeedScore: number;
};
```
