#!/usr/bin/env python3
"""
Get Production Supabase Credentials
Purpose: Extract production credentials for Vercel environment setup
"""

import subprocess
import json
import sys

def get_supabase_projects():
    """Get list of Supabase projects"""
    try:
        result = subprocess.run(['supabase', 'projects', 'list', '--output', 'json'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            print(f"Error getting projects: {result.stderr}")
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def main():
    print("🔍 Getting Production Supabase Credentials")
    print("=" * 50)
    
    projects = get_supabase_projects()
    if not projects:
        print("❌ Could not get Supabase projects")
        return
    
    # Find the linked project (LifeKbServer)
    linked_project = None
    for project in projects:
        if project.get('name') == 'LifeKbServer':
            linked_project = project
            break
    
    if not linked_project:
        print("❌ Could not find LifeKbServer project")
        print("Available projects:")
        for project in projects:
            print(f"  - {project.get('name')} ({project.get('reference_id')})")
        return
    
    ref_id = linked_project.get('reference_id')
    print(f"✅ Found LifeKbServer project: {ref_id}")
    
    # Generate the production URLs and keys
    supabase_url = f"https://{ref_id}.supabase.co"
    
    print("\n📋 Production Environment Variables")
    print("=" * 50)
    print(f"SUPABASE_URL={supabase_url}")
    print("SUPABASE_SERVICE_KEY=<Get from Supabase Dashboard > Settings > API > service_role key>")
    print("SUPABASE_ANON_KEY=<Get from Supabase Dashboard > Settings > API > anon public key>")
    print("JWT_SECRET_KEY=<Generate a secure 32+ character string>")
    print("OPENAI_API_KEY=<Your OpenAI API key (optional)>")
    
    print(f"\n🌐 Supabase Dashboard URL:")
    print(f"https://supabase.com/dashboard/project/{ref_id}/settings/api")
    
    print(f"\n📝 Next Steps:")
    print("1. Go to the Supabase Dashboard URL above")
    print("2. Copy the service_role and anon keys")
    print("3. Generate a secure JWT secret")
    print("4. Run the following commands to set Vercel environment variables:")
    print()
    print(f"vercel env add SUPABASE_URL production")
    print(f"# Enter: {supabase_url}")
    print()
    print("vercel env add SUPABASE_SERVICE_KEY production")
    print("# Enter: <service_role key from dashboard>")
    print()
    print("vercel env add SUPABASE_ANON_KEY production")
    print("# Enter: <anon key from dashboard>")
    print()
    print("vercel env add JWT_SECRET_KEY production")
    print("# Enter: <your secure 32+ character secret>")
    print()
    print("vercel env add OPENAI_API_KEY production")
    print("# Enter: <your OpenAI API key (optional)>")

if __name__ == "__main__":
    main() 