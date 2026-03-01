export type SearchDocType =
  | "episode"
  | "span"
  | "place"
  | "entity"
  | "keyword"
  | "cluster_keyword"
  | "cluster_entity";

export type SearchDoc = {
  id: string;
  type: SearchDocType;
  episodeId?: number;
  clusterId?: number;
  title?: string;
  text: string;
  fields?: Record<string, string>;
};
