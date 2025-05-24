#!/usr/bin/env python3
"""
LifeKB Production Setup Script
Purpose: Automate production deployment setup and validation
"""

import os
import sys
import subprocess
import json
import time
from typing import Dict, List, Optional
import requests

class ProductionSetup:
    def __init__(self):
        self.vercel_url = None
        self.supabase_url = None
        self.required_env_vars = [
            'SUPABASE_URL',
            'SUPABASE_SERVICE_KEY', 
            'SUPABASE_ANON_KEY',
            'JWT_SECRET_KEY'
        ]
        self.optional_env_vars = [
            'OPENAI_API_KEY'
        ]
    
    def check_prerequisites(self) -> bool:
        """Check if required tools are installed"""
        print("🔍 Checking prerequisites...")
        
        tools = {
            'vercel': 'vercel --version',
            'supabase': 'supabase --version',
            'curl': 'curl --version'
        }
        
        for tool, command in tools.items():
            try:
                result = subprocess.run(command.split(), 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"✅ {tool} is installed")
                else:
                    print(f"❌ {tool} is not installed or not working")
                    return False
            except FileNotFoundError:
                print(f"❌ {tool} is not installed")
                return False
        
        return True
    
    def deploy_to_vercel(self) -> Optional[str]:
        """Deploy the application to Vercel"""
        print("\n🚀 Deploying to Vercel...")
        
        try:
            # Deploy with production flag
            result = subprocess.run(['vercel', '--prod', '--yes'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                # Extract URL from output
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'https://' in line and 'vercel.app' in line:
                        self.vercel_url = line.strip()
                        print(f"✅ Deployed successfully to: {self.vercel_url}")
                        return self.vercel_url
                        
                print("⚠️ Deployment succeeded but couldn't extract URL")
                print(result.stdout)
                return None
            else:
                print(f"❌ Deployment failed: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"❌ Deployment error: {e}")
            return None
    
    def configure_environment_variables(self, env_vars: Dict[str, str]) -> bool:
        """Configure environment variables in Vercel"""
        print("\n🔧 Configuring environment variables...")
        
        success_count = 0
        for var_name, var_value in env_vars.items():
            try:
                cmd = ['vercel', 'env', 'add', var_name, 'production']
                
                # Use subprocess.Popen for interactive input
                process = subprocess.Popen(cmd, stdin=subprocess.PIPE, 
                                         stdout=subprocess.PIPE, 
                                         stderr=subprocess.PIPE, text=True)
                
                output, error = process.communicate(input=var_value + '\n')
                
                if process.returncode == 0:
                    print(f"✅ Set {var_name}")
                    success_count += 1
                else:
                    print(f"❌ Failed to set {var_name}: {error}")
                    
            except Exception as e:
                print(f"❌ Error setting {var_name}: {e}")
        
        print(f"📊 Successfully configured {success_count}/{len(env_vars)} variables")
        return success_count == len(env_vars)
    
    def test_health_endpoint(self, url: str) -> bool:
        """Test the health endpoint"""
        print(f"\n🩺 Testing health endpoint: {url}/api/auth?health=true")
        
        try:
            response = requests.get(f"{url}/api/auth?health=true", timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'healthy':
                    print("✅ Health check passed")
                    return True
                else:
                    print(f"⚠️ Health check returned: {data}")
                    return False
            else:
                print(f"❌ Health check failed: {response.status_code}")
                print(response.text)
                return False
                
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
    
    def test_authentication(self, url: str) -> bool:
        """Test authentication endpoints"""
        print(f"\n🔐 Testing authentication...")
        
        # Test user registration
        test_email = f"test-{int(time.time())}@example.com"
        test_password = "TestPass123!"
        
        try:
            # Test signup
            signup_data = {
                "action": "signup",
                "email": test_email,
                "password": test_password
            }
            
            response = requests.post(f"{url}/api/auth", 
                                   json=signup_data, timeout=30)
            
            if response.status_code in [200, 201]:
                print("✅ User registration works")
                
                # Test login
                login_data = {
                    "action": "login", 
                    "email": test_email,
                    "password": test_password
                }
                
                response = requests.post(f"{url}/api/auth",
                                       json=login_data, timeout=30)
                
                if response.status_code == 200:
                    print("✅ User login works")
                    return True
                else:
                    print(f"⚠️ Login failed: {response.status_code}")
                    return False
                    
            else:
                print(f"⚠️ Registration failed: {response.status_code}")
                print(response.text)
                return False
                
        except Exception as e:
            print(f"❌ Authentication test error: {e}")
            return False
    
    def run_deployment_checklist(self) -> None:
        """Run complete deployment checklist"""
        print("🎯 LifeKB Production Deployment")
        print("=" * 50)
        
        checklist = [
            ("Prerequisites", self.check_prerequisites),
        ]
        
        # Run prerequisite checks
        for step_name, step_func in checklist:
            print(f"\n📋 {step_name}")
            if not step_func():
                print(f"❌ {step_name} failed. Please fix and try again.")
                return
        
        # Get environment variables from user
        print("\n📝 Environment Variable Configuration")
        print("Please provide the following environment variables:")
        
        env_vars = {}
        
        # Required variables
        for var in self.required_env_vars:
            value = input(f"Enter {var}: ").strip()
            if not value:
                print(f"❌ {var} is required")
                return
            env_vars[var] = value
        
        # Optional variables
        for var in self.optional_env_vars:
            value = input(f"Enter {var} (optional, press enter to skip): ").strip()
            if value:
                env_vars[var] = value
        
        # Deploy to Vercel
        url = self.deploy_to_vercel()
        if not url:
            print("❌ Deployment failed")
            return
        
        # Configure environment variables
        if not self.configure_environment_variables(env_vars):
            print("⚠️ Some environment variables failed to configure")
        
        # Wait for deployment to be ready
        print("\n⏳ Waiting for deployment to be ready...")
        time.sleep(30)
        
        # Run tests
        print("\n🧪 Running production tests...")
        
        tests_passed = 0
        total_tests = 2
        
        if self.test_health_endpoint(url):
            tests_passed += 1
        
        if self.test_authentication(url):
            tests_passed += 1
        
        # Summary
        print("\n" + "=" * 50)
        print("🎉 DEPLOYMENT SUMMARY")
        print("=" * 50)
        print(f"Deployment URL: {url}")
        print(f"Tests Passed: {tests_passed}/{total_tests}")
        
        if tests_passed == total_tests:
            print("✅ Production deployment successful!")
            print("\n🎯 Next Steps:")
            print("1. Test all API endpoints manually")
            print("2. Configure custom domain (optional)")
            print("3. Set up monitoring and alerts")
            print("4. Run full test suite")
        else:
            print("⚠️ Deployment completed with some test failures")
            print("Please check the logs and fix any issues")

def main():
    setup = ProductionSetup()
    setup.run_deployment_checklist()

if __name__ == "__main__":
    main() 