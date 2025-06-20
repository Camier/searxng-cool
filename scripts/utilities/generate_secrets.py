#!/usr/bin/env python3
"""
Secret Generation Utility
Generates secure secrets for configuration
"""
import os
import secrets
import string
import argparse


def generate_secret(length: int = 32, charset: str = 'hex') -> str:
    """Generate a secure secret"""
    if charset == 'hex':
        return secrets.token_hex(length)
    elif charset == 'urlsafe':
        return secrets.token_urlsafe(length)
    elif charset == 'alphanumeric':
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    elif charset == 'full':
        alphabet = string.ascii_letters + string.digits + string.punctuation
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    else:
        raise ValueError(f"Unknown charset: {charset}")


def main():
    parser = argparse.ArgumentParser(description='Generate secure secrets')
    parser.add_argument('--type', choices=['jwt', 'flask', 'password', 'api-key', 'all'], 
                        default='all', help='Type of secret to generate')
    parser.add_argument('--length', type=int, default=32, 
                        help='Length of the secret (default: 32)')
    parser.add_argument('--charset', choices=['hex', 'urlsafe', 'alphanumeric', 'full'],
                        default='hex', help='Character set to use')
    
    args = parser.parse_args()
    
    print("🔐 Secure Secret Generator\n")
    
    if args.type == 'all' or args.type == 'jwt':
        jwt_secret = generate_secret(32, 'hex')
        print("JWT_SECRET_KEY:")
        print(f"  {jwt_secret}")
        print(f"  Length: {len(jwt_secret)} characters")
        print()
    
    if args.type == 'all' or args.type == 'flask':
        flask_secret = generate_secret(32, 'hex')
        print("SECRET_KEY (Flask):")
        print(f"  {flask_secret}")
        print(f"  Length: {len(flask_secret)} characters")
        print()
    
    if args.type == 'all' or args.type == 'password':
        # Generate a strong password
        password = generate_secret(16, 'alphanumeric')
        print("Database Password:")
        print(f"  {password}")
        print(f"  Length: {len(password)} characters")
        print()
    
    if args.type == 'all' or args.type == 'api-key':
        # Generate API key
        api_key = generate_secret(32, 'alphanumeric')
        print("API Key:")
        print(f"  {api_key}")
        print(f"  Length: {len(api_key)} characters")
        print()
    
    if args.type != 'all':
        # Generate custom secret
        secret = generate_secret(args.length, args.charset)
        print(f"Custom Secret ({args.charset}):")
        print(f"  {secret}")
        print(f"  Length: {len(secret)} characters")
    
    print("\n💡 Tips:")
    print("  - Copy these values to your .env file")
    print("  - Never commit secrets to version control")
    print("  - Rotate secrets periodically")
    print("  - Use different secrets for each environment")


if __name__ == "__main__":
    main()