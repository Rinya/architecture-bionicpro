// Token Service for handling Keycloak to Backend token exchange
let backendTokenCache: {
  token: string;
  expiresAt: number;
} | null = null;

// Utility function to safely parse JSON and replace NaN values
export const safeParseJson = async (response: Response): Promise<any> => {
  const text = await response.text();
  try {
    // Replace NaN values with 0 before parsing
    const cleanedText = text.replace(/:\s*NaN\s*/g, ': 0')
                          .replace(/:\s*Infinity\s*/g, ': 0')
                          .replace(/:\s*-Infinity\s*/g, ': 0');
    return JSON.parse(cleanedText);
  } catch (error) {
    console.error('JSON parsing error:', error);
    console.error('Original text:', text);
    throw new Error('Invalid JSON response from server');
  }
};

interface TokenExchangeResponse {
  access_token: string;
  user_id: string;
  expires_in: number;
}

export const exchangeKeycloakToken = async (keycloakToken: string): Promise<string> => {
  // Check if we have a valid cached token
  if (backendTokenCache && backendTokenCache.expiresAt > Date.now()) {
    return backendTokenCache.token;
  }

  try {
    const response = await fetch(`${process.env.REACT_APP_API_URL}/auth/keycloak-exchange`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${keycloakToken}`,
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      throw new Error(`Token exchange failed: ${response.statusText}`);
    }

    const data: TokenExchangeResponse = await safeParseJson(response);

    // Cache the backend token (subtract 5 minutes for safety)
    backendTokenCache = {
      token: data.access_token,
      expiresAt: Date.now() + (data.expires_in * 1000) - (5 * 60 * 1000)
    };

    return data.access_token;
  } catch (error) {
    console.error('Token exchange failed:', error);
    throw error;
  }
};

export const makeAuthenticatedRequest = async (
  url: string,
  keycloakToken: string,
  options: RequestInit = {}
): Promise<Response> => {
  try {
    const backendToken = await exchangeKeycloakToken(keycloakToken);

    const authenticatedOptions = {
      ...options,
      headers: {
        ...options.headers,
        'Authorization': `Bearer ${backendToken}`,
        'Accept': 'application/json'
      }
    };

    return fetch(url, authenticatedOptions);
  } catch (error) {
    console.error('Authenticated request failed:', error);
    throw error;
  }
};

export const clearTokenCache = (): void => {
  backendTokenCache = null;
};