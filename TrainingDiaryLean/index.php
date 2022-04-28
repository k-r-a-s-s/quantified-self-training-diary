<?php 

require_once __DIR__ . "/vendor/autoload.php";



if (!function_exists('str_putcsv')) {
    function str_putcsv($input, $delimiter = ',', $enclosure = '"') {
        $fp = fopen('php://temp', 'r+b');
        fputcsv($fp, $input, $delimiter, $enclosure);
        rewind($fp);
        $data = rtrim(stream_get_contents($fp), "\n");
        fclose($fp);
        return $data;
    }
}

use djchen\OAuth2\Client\Provider\Fitbit;

$provider = new Fitbit([
    'clientId'          => '  ',
    'clientSecret'      => '  ',
    'redirectUri'       => 'http://localhost:8080/'
]);

// start the session
session_start();

// If we don't have an authorization code then get one
if (!isset($_GET['code'])) {

    // Fetch the authorization URL from the provider; this returns the
    // urlAuthorize option and generates and applies any necessary parameters
    // (e.g. state).
    $authorizationUrl = $provider->getAuthorizationUrl();

    // Get the state generated for you and store it to the session.
    $_SESSION['oauth2state'] = $provider->getState();

    // Redirect the user to the authorization URL.
    header('Location: ' . $authorizationUrl);
    exit;

// Check given state against previously stored one to mitigate CSRF attack
} elseif (empty($_GET['state']) || array_key_exists('oauth2state', $_SESSION) && ($_GET['state'] !== $_SESSION['oauth2state'])) {
    unset($_SESSION['oauth2state']);
    exit('Invalid state');

} else {

    try {

        // Try to get an access token using the authorization code grant.
        $accessToken = $provider->getAccessToken('authorization_code', [
            'code' => $_GET['code']
        ]);

        // We have an access token, which we may use in authenticated
        // requests against the service provider's API.
        echo $accessToken->getToken() . "\n";
        echo $accessToken->getRefreshToken() . "\n";
        echo $accessToken->getExpires() . "\n";
        echo ($accessToken->hasExpired() ? 'expired' : 'not expired') . "\n";

        // Using the access token, we may look up details about the
        // resource owner.
        $resourceOwner = $provider->getResourceOwner($accessToken);
        
        // set time zone and get the current date in string format
        date_default_timezone_set('Australia/Melbourne');
        $current_date = date('Y-m-d', time());
        
        // create a datetime object, subtract thritry days and then convert in to string format
        $start_date = DateTime::createFromFormat('Y-m-d', $current_date);
        date_sub($start_date, date_interval_create_from_date_string('90 days'));
        $start_date = $start_date->format('Y-m-d');
        
        // sub in start and current date in to url builder to access API
        $sleep_string_url = "/1.2/user/-/sleep/date/". $start_date . "/" . $current_date . ".json";
        $heart_string_url = "/1/user/-/activities/heart/date/" . $start_date . "/" . $current_date . ".json";

        var_export($resourceOwner->toArray());

        // The provider provides a way to get an authenticated API request for
        // the service, using the access token; it returns an object conforming
        // to Psr\Http\Message\RequestInterface.
        $request = $provider->getAuthenticatedRequest(
            Fitbit::METHOD_GET,
            Fitbit::BASE_FITBIT_API_URL . $sleep_string_url,
            $accessToken,
            ['headers' => [Fitbit::HEADER_ACCEPT_LANG => 'en_US'], [Fitbit::HEADER_ACCEPT_LOCALE => 'en_US']]
            // Fitbit uses the Accept-Language for setting the unit system used
            // and setting Accept-Locale will return a translated response if available.
            // https://dev.fitbit.com/docs/basics/#localization
        );
        // Make the authenticated API request and get the parsed response.
        $response = $provider->getParsedResponse($request);
            
        echo "\n";
        var_dump($response);
        
        //save database
        $fp1 = fopen('results_sleep.json', 'w');
        fwrite($fp1, json_encode($response));
        fclose($fp1);
        
        
                // The provider provides a way to get an authenticated API request for
        // the service, using the access token; it returns an object conforming
        // to Psr\Http\Message\RequestInterface.
        $request = $provider->getAuthenticatedRequest(
            Fitbit::METHOD_GET,
            Fitbit::BASE_FITBIT_API_URL . $heart_string_url,
            $accessToken,
            ['headers' => [Fitbit::HEADER_ACCEPT_LANG => 'en_US'], [Fitbit::HEADER_ACCEPT_LOCALE => 'en_US']]
            // Fitbit uses the Accept-Language for setting the unit system used
            // and setting Accept-Locale will return a translated response if available.
            // https://dev.fitbit.com/docs/basics/#localization
        );
        // Make the authenticated API request and get the parsed response.
        $response2 = $provider->getParsedResponse($request);
        
        
        
        
                //save database
        $fp2 = fopen('results_heart.json', 'w');
        fwrite($fp2, json_encode($response2));
        fclose($fp2);
        
        
        ///save token
        $fp = fopen('creds/FitBitCred.txt', 'w');
        fwrite($fp, $accessToken);
        fclose($fp);

        // If you would like to get the response headers in addition to the response body, use:
        //$response = $provider->getResponse($request);
        //$headers = $response->getHeaders();
        //$parsedResponse = $provider->parseResponse($response);

    } catch (\League\OAuth2\Client\Provider\Exception\IdentityProviderException $e) {

        // Failed to get the access token or user details.
        exit($e->getMessage());

    }

}





?>
