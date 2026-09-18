import {createBrowserClient} from '@supabase/ssr';
let client:ReturnType<typeof createBrowserClient>|undefined;
export function getAuthClient(){
 const url=process.env.NEXT_PUBLIC_SUPABASE_URL,key=process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
 if(!url||!key)return null;
 return client??=createBrowserClient(url,key);
}
export const mockMode=process.env.NEXT_PUBLIC_USE_MOCK_API==='true';
