import jwt

# --- PASTE YOUR JWT_SECRET HERE ---
# Keep the single quotes around it.
jwt_secret = 'YOUR_JWT_SECRET_FROM_STEP_5.1_HERE'

# --- Payloads (no need to change) ---
anon_payload = {'role': 'anon'}
service_role_payload = {'role': 'service_role'}

# --- Generate the tokens ---
# The 'HS256' algorithm is Supabase's default.
anon_key = jwt.encode(anon_payload, jwt_secret, algorithm='HS256')
service_role_key = jwt.encode(service_role_payload, jwt_secret, algorithm='HS256')

# --- Print the results ---
print("\n--- YOUR GENERATED KEYS ---")
print("\n[ANON_KEY]")
print(anon_key)
print("\n[SERVICE_ROLE_KEY]")
print(service_role_key)
print("\nCopy and paste these values into your .env file\n")
