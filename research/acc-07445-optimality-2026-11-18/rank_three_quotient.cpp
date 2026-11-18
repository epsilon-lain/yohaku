#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

using State = std::array<std::string, 3>;
using Clock = std::chrono::steady_clock;

constexpr int orders[6][3] = {
    {0, 1, 2}, {0, 2, 1}, {1, 0, 2}, {1, 2, 0}, {2, 0, 1}, {2, 1, 0},
};

char inverse(char letter) {
    return static_cast<char>('1' + ((letter - '1') ^ 1));
}

void append_reduced(std::string& word, char letter) {
    if (!word.empty() && word.back() == inverse(letter)) {
        word.pop_back();
    } else {
        word.push_back(letter);
    }
}

std::string canonical(const State& state) {
    std::string best;
    std::string candidate;
    for (const auto& order : orders) {
        if (state[order[0]].size() > state[order[1]].size() ||
            state[order[1]].size() > state[order[2]].size()) {
            continue;
        }
        // With rows fixed, first occurrences give the lexicographically least
        // unsigned generator renaming, regardless of the sign of that occurrence.
        std::array<int, 3> renamed{};
        int next = '1';
        candidate.clear();
        for (const int row : order) {
            for (const char letter : state[row]) {
                const int code = letter - '1';
                int& label = renamed[code / 2];
                if (label == 0) {
                    label = next;
                    next += 2;
                }
                candidate.push_back(static_cast<char>(label + code % 2));
            }
            candidate.push_back('0');
        }
        if (best.empty() || candidate < best) {
            best.swap(candidate);
        }
    }
    return best;
}

State decode(const std::string& key) {
    State state;
    std::size_t offset = 0;
    for (std::string& word : state) {
        const auto end = key.find('0', offset);
        if (end == std::string::npos) {
            throw std::runtime_error("malformed state");
        }
        word = key.substr(offset, end - offset);
        offset = end + 1;
    }
    if (offset != key.size()) {
        throw std::runtime_error("trailing state data");
    }
    return state;
}

struct Move {
    int id;
    int kind;
    int row;
    int argument;
};

template<class Visit>
bool for_children(const State& state, const std::vector<Move>& moves, Visit visit) {
    State candidate = state;
    State inverses;
    for (int row = 0; row < 3; ++row) {
        for (auto it = state[row].rbegin(); it != state[row].rend(); ++it) {
            inverses[row].push_back(inverse(*it));
        }
    }
    for (const Move move : moves) {
        auto& modified = candidate[move.row];
        if (move.kind == 0) {
            modified = inverses[move.row];
        } else if (move.kind == 1 || move.kind == 2) {
            const auto& donor = move.kind == 1 ? state[move.argument] : inverses[move.argument];
            for (const char letter : donor) {
                append_reduced(modified, letter);
            }
        } else {
            const char letter = static_cast<char>(move.argument);
            modified.assign(1, letter);
            for (const char original : state[move.row]) {
                append_reduced(modified, original);
            }
            append_reduced(modified, inverse(letter));
        }
        if (modified != state[move.row] && visit(move, candidate)) {
            return true;
        }
        modified = state[move.row];
    }
    return false;
}

using Parents = std::unordered_map<std::string, const std::string*>;

struct Ball {
    Parents parents;
    std::vector<const std::string*> layer;
    std::vector<std::uint64_t> layer_sizes;
    std::uint64_t edges = 0;
};

Ball ball(const std::string& root, unsigned radius, const std::vector<Move>& moves,
          const Clock::time_point deadline, std::size_t limit, const char* name) {
    Ball ball;
    ball.parents.reserve(std::min<std::size_t>(limit, 1'000'000));
    ball.layer = {&ball.parents.emplace(root, nullptr).first->first};
    ball.layer_sizes = {1};
    for (unsigned depth = 1; depth <= radius; ++depth) {
        std::vector<const std::string*> next_layer;
        std::size_t checked = 0;
        for (const auto* parent : ball.layer) {
            if (++checked % 1024 == 0 && Clock::now() > deadline) {
                throw std::runtime_error(std::string(name) + " time cap at layer " + std::to_string(depth));
            }
            ball.edges += moves.size();
            for_children(decode(*parent), moves, [&](Move, const State& child) {
                const auto [entry, inserted] = ball.parents.emplace(canonical(child), parent);
                if (inserted) {
                    next_layer.push_back(&entry->first);
                    if (ball.parents.size() > limit) {
                        throw std::runtime_error(std::string(name) + " state cap at layer " + std::to_string(depth));
                    }
                }
                return false;
            });
        }
        ball.layer = std::move(next_layer);
        ball.layer_sizes.push_back(ball.layer.size());
        std::cerr << name << " complete layer " << depth << " states " << ball.layer.size() << '\n';
    }
    return ball;
}

void array_json(const auto& values) {
    std::cout << '[';
    bool first = true;
    for (const auto value : values) {
        std::cout << (first ? "" : ",") << value;
        first = false;
    }
    std::cout << ']';
}

int main(int argc, char** argv) try {
    if (argc != 3) {
        throw std::runtime_error("usage: rank_three_quotient MAX_NODES_PER_BALL MAX_SECONDS");
    }
    const std::size_t limit = std::stoull(argv[1]);
    const auto began = Clock::now();
    const auto deadline = began + std::chrono::seconds(std::stoi(argv[2]));
    std::string initial;
    std::vector<Move> moves;
    std::cin >> initial;
    for (Move move; std::cin >> move.id >> move.kind >> move.row >> move.argument;) {
        moves.push_back(move);
    }
    if (initial.empty() || moves.size() != 33) {
        throw std::runtime_error("expected a rank-three state and 33 preserving moves");
    }
    const auto start = decode(initial);
    const auto goal = canonical(State{"1", "3", "5"});
    const auto start_key = canonical(start);
    const auto reverse = ball(goal, 5, moves, deadline, limit, "reverse");
    const auto forward = ball(start_key, 4, moves, deadline, limit, "forward");

    const std::string* forward_join = nullptr;
    const std::string* reverse_join = nullptr;
    for (const auto& [node, parent] : forward.parents) {
        if (const auto it = reverse.parents.find(node); it != reverse.parents.end()) {
            forward_join = &node;
            reverse_join = it->second;
            break;
        }
    }
    std::uint64_t shell_edges = 0;
    if (forward_join == nullptr) {
        for (const auto* node : forward.layer) {
            if ((shell_edges / moves.size()) % 1024 == 0 && Clock::now() > deadline) {
                throw std::runtime_error("time cap in streamed forward layer 5");
            }
            shell_edges += moves.size();
            if (for_children(decode(*node), moves, [&](Move, const State& child) {
                    const auto it = reverse.parents.find(canonical(child));
                    if (it == reverse.parents.end()) {
                        return false;
                    }
                    forward_join = node;
                    reverse_join = &it->first;
                    return true;
                })) {
                break;
            }
        }
    }
    std::vector<int> witness;
    if (forward_join != nullptr) {
        std::vector<const std::string*> path;
        for (auto step = forward_join; step != nullptr; step = forward.parents.at(*step)) {
            path.push_back(step);
        }
        std::reverse(path.begin(), path.end());
        for (auto step = reverse_join; step != nullptr; step = reverse.parents.at(*step)) {
            path.push_back(step);
        }
        State current = start;
        for (std::size_t i = 1; i < path.size(); ++i) {
            State next_state;
            const bool lifted = for_children(current, moves, [&](Move move, const State& child) {
                if (canonical(child) != *path[i]) {
                    return false;
                }
                witness.push_back(move.id);
                next_state = child;
                return true;
            });
            if (!lifted) {
                throw std::runtime_error("quotient path did not lift");
            }
            current = std::move(next_state);
        }
        if (canonical(current) != goal) {
            throw std::runtime_error("lifted path did not reach the target orbit");
        }
    }
    std::cout << "{\n  \"reverse_orbit_layers\": ";
    array_json(reverse.layer_sizes);
    std::cout << ",\n  \"forward_orbit_layers\": ";
    array_json(forward.layer_sizes);
    std::cout << ",\n  \"exact_ball_edge_slots\": " << (reverse.edges + forward.edges)
              << ",\n  \"forward_shell_edge_slots\": " << shell_edges
              << ",\n  \"elapsed_seconds\": " << std::chrono::duration<double>(Clock::now() - began).count()
              << ",\n  \"rank_preserving_witness\": ";
    if (forward_join == nullptr) {
        std::cout << "null";
    } else {
        array_json(witness);
    }
    std::cout << "\n}\n";
} catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 2;
}
