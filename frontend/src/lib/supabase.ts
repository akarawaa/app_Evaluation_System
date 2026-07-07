import { createClient } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL as string
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string

// Client gets the ANON key only (never service_role). Auth session is persisted
// by supabase-js; the access token carries the tenant claims the backend reads.
export const supabase = createClient(url, anonKey)
