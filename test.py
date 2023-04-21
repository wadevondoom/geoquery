from ping3 import ping, verbose_ping

# Replace '8.8.8.8' with the IP address or hostname you want to ping
target = '8.8.8.8'

try:
    response_time = ping(target)
    if response_time is not None:
        print(f'Ping to {target} succeeded with response time: {response_time} ms')
    else:
        print(f'Ping to {target} failed. No response.')

    print('\nVerbose ping output:')
    verbose_ping(target)
except PermissionError:
    print('PermissionError: You need to run this script as root or with the necessary capabilities.')
except Exception as e:
    print(f'An error occurred: {e}')