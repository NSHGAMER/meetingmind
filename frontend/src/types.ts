export interface User { id: number; email: string; name: string }
export interface Contact {
  id: number; full_name: string; email?: string | null; organization?: string | null; job_title?: string | null;
  description?: string | null; relationship_notes?: string | null; is_sample: boolean;
}
export interface Meeting {
  id: number; title: string; organization?: string | null; objective?: string | null; agenda?: string | null;
  scheduled_at: string; status: "scheduled" | "completed" | "cancelled"; notes?: string | null;
  analysis_status: "none" | "pending_confirmation" | "confirmed"; is_sample: boolean; participants: Contact[];
}
export interface Commitment {
  id: number; description: string; owner_name: string; owner_contact_id: number | null; meeting_id: number;
  meeting_title: string; meeting_date: string; created_at: string; due_date: string | null;
  status: string; stored_status: string; is_sample: boolean;
}
export interface Extraction {
  summary: string; participants: string[]; topics: string[];
  discussions: { text: string; topic?: string | null }[];
  decisions: { text: string; status: "approved" | "rejected" | "proposed" }[];
  commitments: { description: string; owner_name: string; due_date?: string | null; kind: "commitment" | "suggestion"; evidence?: string | null }[];
  concerns: { text: string; raised_by?: string | null }[];
  preferences: { text: string; person?: string | null }[];
  unresolved: string[]; follow_ups: string[];
  suggested_status_updates: { commitment_id: number; suggested_status: string; evidence?: string | null }[];
}
export interface MeetingRef { id: number; title: string; date: string }
export interface Reference { kind: "memory" | "commitment"; text: string; source_meeting: MeetingRef | null; type?: string | null }
export interface Cited { text: string; sources: string[]; reason?: string }
export interface Briefing {
  id: number; mode: "memory" | "generic"; requested_mode: string; memory_used: boolean; memories_retrieved: number;
  generated_at: string; notes: string[]; processing_notice?: string;
  overview: { title: string; objective?: string | null; participants: { id: number; name: string; job_title?: string; organization?: string }[]; previous_meetings: MeetingRef[] };
  pending_commitments: { ref: string; id: number; owner_name: string; description: string; due_date: string | null; status: string; source_meeting: MeetingRef | null }[];
  draft: { previous_interactions_summary: string; historical_context: Cited[]; previous_concerns: Cited[]; things_to_remember: Cited[]; talking_points: Cited[]; strategy: string[] };
  references: Record<string, Reference>;
}
