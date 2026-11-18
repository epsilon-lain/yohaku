#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>
#include <sys/resource.h>
#include <unistd.h>

using Index = uint32_t;
constexpr Index missing = std::numeric_limits<Index>::max();
using State = std::array<Index, 3>;
using Clock = std::chrono::steady_clock;

struct Move {
    int id;
    char category;
    int slot;
    int argument;
    bool invert_other;
    int inverse;
};

char inverse_letter(char letter) {
    return static_cast<char>(letter ^ 4);
}

std::string changed_word(const std::array<const std::string *, 3>& words, const Move& move) {
    const auto& word = *words[move.slot];
    if (move.category == 'I') {
        std::string result(word.rbegin(), word.rend());
        for (char& letter : result) letter = inverse_letter(letter);
        return result;
    }
    if (move.category == 'M') {
        const auto& other = *words[move.argument];
        std::string result = word;
        if (move.invert_other) {
            for (auto letter = other.rbegin(); letter != other.rend(); ++letter) {
                char next = inverse_letter(*letter);
                if (!result.empty() && result.back() == inverse_letter(next)) result.pop_back();
                else result.push_back(next);
            }
        } else {
            for (char letter : other) {
                if (!result.empty() && result.back() == inverse_letter(letter)) result.pop_back();
                else result.push_back(letter);
            }
        }
        return result;
    }
    const char letter = static_cast<char>('0' + move.argument);
    std::string result(1, letter);
    if (!word.empty() && word.front() == inverse_letter(letter)) {
        result.assign(word.begin() + 1, word.end());
    } else {
        result += word;
    }
    if (!result.empty() && result.back() == letter) result.pop_back();
    else result.push_back(inverse_letter(letter));
    return result;
}

struct Words {
    std::unordered_map<std::string, Index> by_word;
    std::vector<const std::string*> by_id;

    Index find(const std::string& word) const {
        const auto entry = by_word.find(word);
        return entry == by_word.end() ? missing : entry->second;
    }

    Index insert(std::string word) {
        const auto [entry, inserted] = by_word.try_emplace(std::move(word), by_id.size());
        if (inserted) by_id.push_back(&entry->first);
        return entry->second;
    }

    std::array<const std::string *, 3> decode(const State& state) const {
        return {by_id[state[0]], by_id[state[1]], by_id[state[2]]};
    }
};

struct StateHash {
    size_t operator()(const State& state) const {
        uint64_t value = uint64_t(state[0]) * 0x9e3779b185ebca87ULL
                       + uint64_t(state[1]) * 0xc2b2ae3d27d4eb4fULL
                       + uint64_t(state[2]) * 0x165667b19e3779f9ULL;
        return value ^ (value >> 32);
    }
};

struct Node {
    State state;
    Index parent;
    int move;
    unsigned depth;
};

struct Ball {
    std::vector<Node> nodes;
    std::unordered_map<State, Index, StateHash> seen;
    std::vector<size_t> ends{0};

    bool push(const State& state, Index parent, int move, unsigned depth) {
        const auto [entry, inserted] = seen.try_emplace(state, nodes.size());
        if (inserted) nodes.push_back({state, parent, move, depth});
        return inserted;
    }

    unsigned radius() const {
        return ends.size() - 2;
    }

    Index find(const State& state) const {
        const auto entry = seen.find(state);
        return entry == seen.end() ? missing : entry->second;
    }
};

uint64_t stationary_pair(const State& state, int omitted) {
    return (uint64_t(state[(omitted + 1) % 3]) << 32) | state[(omitted + 2) % 3];
}

struct Guard : std::runtime_error {
    using std::runtime_error::runtime_error;
};

struct Search {
    Words words;
    Ball forward;
    Ball reverse;
    std::vector<Move> moves;
    std::array<Move, 257> by_id{};
    std::array<std::vector<Move>, 3> by_slot;
    std::array<std::unordered_set<uint64_t>, 3> projection;
    std::vector<int> best;
    const Clock::time_point started = Clock::now();
    size_t state_cap;
    double seconds_cap;
    size_t rss_cap_kib;
    const unsigned radius_cap;
    uint64_t stored_edges = 0;
    uint64_t stored_intersections = 0;
    uint64_t shell_edges = 0;
    uint64_t one_edge_intersections = 0;
    uint64_t two_edge_intersections = 0;
    uint64_t projection_matches = 0;
    uint64_t exact_inverse_checks = 0;
    size_t shell_sources_scanned = 0;
    bool stored_join_complete = false;
    bool shell_complete = false;
    std::string stage = "build";
    std::string guard;

    double elapsed() const {
        return std::chrono::duration<double>(Clock::now() - started).count();
    }

    void check_budget() const {
        if (elapsed() >= seconds_cap) throw Guard("wall_time_cap");
        std::ifstream memory("/proc/self/statm");
        size_t virtual_pages = 0;
        size_t resident_pages = 0;
        if (memory >> virtual_pages >> resident_pages) {
            const size_t rss_kib = resident_pages * static_cast<size_t>(sysconf(_SC_PAGESIZE)) / 1024;
            if (rss_kib >= rss_cap_kib) throw Guard("resident_memory_cap");
        }
    }

    Search(size_t states, double seconds, size_t rss, unsigned radius)
        : state_cap(states), seconds_cap(seconds), rss_cap_kib(rss), radius_cap(radius) {}

    void load_moves(std::istream& input) {
        for (int index = 0; index < 33; ++index) {
            Move move{};
            if (!(input >> move.id >> move.category >> move.slot >> move.argument >>
                   move.invert_other >> move.inverse)) {
                throw std::runtime_error("incomplete preserving move table");
            }
            moves.push_back(move);
            by_id[move.id] = move;
            by_slot[move.slot].push_back(move);
        }
    }

    void grow(Ball& ball, bool backward) {
        const auto radius = ball.radius();
        for (size_t index = ball.ends[radius]; index < ball.ends[radius + 1]; ++index) {
            if (index % 512 == 0) check_budget();
            const State parent = ball.nodes[index].state;
            const auto decoded = words.decode(parent);
            for (const Move& move : moves) {
                ++stored_edges;
                State state = parent;
                state[move.slot] = words.insert(changed_word(decoded, move));
                if (forward.nodes.size() + reverse.nodes.size() >= state_cap) {
                    throw Guard("stored_state_cap");
                }
                ball.push(state, index, backward ? move.inverse : move.id, radius + 1);
            }
        }
        ball.ends.push_back(ball.nodes.size());
        std::cerr << (backward ? "reverse" : "forward") << " radius " << ball.radius()
                  << " total " << ball.nodes.size() << " seconds " << elapsed() << '\n';
    }

    void consider(Index left, const std::vector<int>& middle, Index right) {
        for (const auto index : {left, right}) {
            if (index == missing) throw std::runtime_error("missing witness arm");
        }
        std::vector<int> path;
        for (Index index = left; forward.nodes[index].parent != missing; index = forward.nodes[index].parent) {
            path.push_back(forward.nodes[index].move);
        }
        std::reverse(path.begin(), path.end());
        path.insert(path.end(), middle.begin(), middle.end());
        for (Index index = right; reverse.nodes[index].parent != missing; index = reverse.nodes[index].parent) {
            path.push_back(reverse.nodes[index].move);
        }
        if (best.empty() || path.size() < best.size()) best = std::move(path);
    }

    void join_stored() {
        for (Index left = 0; left < forward.nodes.size(); ++left) {
            if (left % 2048 == 0) check_budget();
            const Index right = reverse.find(forward.nodes[left].state);
            if (right != missing) {
                ++stored_intersections;
                consider(left, {}, right);
            }
        }
        stored_join_complete = true;
    }

    void join_shell() {
        const unsigned left_radius = forward.radius();
        const unsigned right_radius = reverse.radius();
        const size_t forward_begin = forward.ends[left_radius];
        const size_t forward_end = forward.ends[left_radius + 1];
        for (auto& keys : projection) keys.reserve(forward_end - forward_begin);
        for (size_t left = forward_begin; left < forward_end; ++left) {
            if (left % 2048 == 0) check_budget();
            for (int slot = 0; slot < 3; ++slot) {
                projection[slot].insert(stationary_pair(forward.nodes[left].state, slot));
            }
        }
        const size_t reverse_begin = reverse.ends[right_radius];
        const size_t reverse_end = reverse.ends[right_radius + 1];
        for (Index right = reverse_begin; right < reverse_end; ++right) {
            if (right % 512 == 0) check_budget();
            const State state = reverse.nodes[right].state;
            auto decoded = words.decode(state);
            for (const Move& from_right : moves) {
                ++shell_edges;
                const int changed = from_right.slot;
                const auto new_word = changed_word(decoded, from_right);
                State midpoint = state;
                midpoint[changed] = words.find(new_word);
                if (midpoint[changed] != missing) {
                    const Index left = forward.find(midpoint);
                    if (left != missing) {
                        ++one_edge_intersections;
                        consider(left, {from_right.inverse}, right);
                    }
                }
                auto middle_words = decoded;
                middle_words[changed] = &new_word;
                for (int slot = 0; slot < 3; ++slot) {
                    if (slot != changed && midpoint[changed] == missing) continue;
                    if (!projection[slot].contains(stationary_pair(midpoint, slot))) continue;
                    ++projection_matches;
                    for (const Move& from_middle : by_slot[slot]) {
                        ++exact_inverse_checks;
                        State predecessor = midpoint;
                        predecessor[slot] = words.find(changed_word(middle_words, from_middle));
                        if (predecessor[slot] == missing) continue;
                        const Index left = forward.find(predecessor);
                        if (left != missing && forward.nodes[left].depth == left_radius) {
                            ++two_edge_intersections;
                            consider(left, {from_middle.inverse, from_right.inverse}, right);
                        }
                    }
                }
            }
            ++shell_sources_scanned;
        }
        shell_complete = true;
    }

    void run() {
        try {
            while (forward.radius() < radius_cap || reverse.radius() < radius_cap) {
                const size_t forward_size = forward.ends.back() - forward.ends[forward.radius()];
                const size_t reverse_size = reverse.ends.back() - reverse.ends[reverse.radius()];
                if (reverse.radius() == radius_cap ||
                    (forward.radius() < radius_cap && forward_size <= reverse_size)) {
                    grow(forward, false);
                } else {
                    grow(reverse, true);
                }
            }
        } catch (const Guard& error) {
            guard = error.what();
        }
        stage = "stored_join";
        try {
            join_stored();
            if (!best.empty() || !guard.empty()) return;
            stage = "two_shell_join";
            join_shell();
            stage = "done";
        } catch (const Guard& error) {
            guard = error.what();
        }
    }

    void print_ball(const Ball& ball) const {
        std::cout << "{\"complete_radius\":" << ball.radius() << ",\"states\":" << ball.nodes.size()
                  << ",\"complete_states\":" << ball.ends.back() << ",\"layers\":[";
        for (size_t index = 1; index < ball.ends.size(); ++index) {
            if (index > 1) std::cout << ',';
            std::cout << ball.ends[index] - ball.ends[index-1];
        }
        std::cout << "]}";
    }

    void print_result() const {
        struct rusage usage{};
        if (getrusage(RUSAGE_SELF, &usage) != 0) throw std::runtime_error("getrusage failed");
        std::cout << "{\"forward\":";
        print_ball(forward);
        std::cout << ",\"reverse\":";
        print_ball(reverse);
        std::cout << ",\"stored_edges\":" << stored_edges
                  << ",\"stored_intersections\":" << stored_intersections
                  << ",\"stored_join_complete\":" << (stored_join_complete ? "true" : "false")
                  << ",\"shell_edges\":" << shell_edges
                  << ",\"one_edge_intersections\":" << one_edge_intersections
                  << ",\"two_edge_intersections\":" << two_edge_intersections
                  << ",\"shell_sources_scanned\":" << shell_sources_scanned
                  << ",\"stationary_pair_matches\":" << projection_matches
                  << ",\"exact_inverse_checks\":" << exact_inverse_checks
                  << ",\"shell_complete\":" << (shell_complete ? "true" : "false")
                  << ",\"word_count\":" << words.by_id.size()
                  << ",\"peak_rss_kib\":" << usage.ru_maxrss
                  << ",\"seconds\":" << elapsed()
                  << ",\"stage\":\"" << stage << "\",\"guard\":\"" << guard
                  << "\",\"preserving_witness\":[";
        for (size_t index = 0; index < best.size(); ++index) {
            if (index) std::cout << ',';
            std::cout << best[index];
        }
        std::cout << "]}\n";
    }
};

int main(int argc, char** argv) {
    size_t state_cap = 0;
    double seconds_cap = 0;
    size_t rss_cap = 0;
    unsigned radius = 0;
    if (!(std::cin >> state_cap >> seconds_cap >> rss_cap >> radius)) return EXIT_FAILURE;
    Search search(state_cap, seconds_cap, rss_cap, radius);
    search.load_moves(std::cin);
    if (argc == 2 && std::string(argv[1]) == "--probe") {
        std::array<std::string, 3> input;
        int id;
        while (std::cin >> id >> input[0] >> input[1] >> input[2]) {
            for (auto& word : input) if (word == "_") word.clear();
            const std::array<const std::string*, 3> words{&input[0], &input[1], &input[2]};
            const auto changed = changed_word(words, search.by_id[id]);
            std::cout << (changed.empty() ? "_" : changed) << '\n';
        }
        return EXIT_SUCCESS;
    }
    State start{};
    for (Index& word : start) {
        std::string input;
        if (!(std::cin >> input)) return EXIT_FAILURE;
        if (input == "_") input.clear();
        word = search.words.insert(input);
    }
    search.forward.push(start, missing, -1, 0);
    search.forward.ends.push_back(1);
    std::array<std::string, 3> permutation{"1", "2", "3"};
    do {
        State target{};
        for (size_t i = 0; i < target.size(); ++i) target[i] = search.words.insert(permutation[i]);
        search.reverse.push(target, missing, -1, 0);
    } while (std::next_permutation(permutation.begin(), permutation.end()));
    search.reverse.ends.push_back(search.reverse.nodes.size());
    search.run();
    search.print_result();
}
