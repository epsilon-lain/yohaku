#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <span>
#include <stdexcept>
#include <string>
#include <sys/resource.h>
#include <unordered_map>
#include <unordered_set>
#include <vector>

using Id = uint32_t;
using Key = uint64_t;
using State = std::array<Id, 3>;
using Word = std::string;
using Clock = std::chrono::steady_clock;
constexpr unsigned id_bits = 21;
constexpr Key id_mask = (1ULL << id_bits) - 1;
constexpr int exp_bias = 1024;
constexpr unsigned max_depth = 4;
const auto start_time = Clock::now();

struct Exponents {
    int x = 0;
    int y = 0;
    Exponents operator+(Exponents other) const { return {x + other.x, y + other.y}; }
    Exponents operator-() const { return {-x, -y}; }
};

int letter(char a) { return static_cast<signed char>(a); }
char inverse(char a) { return static_cast<char>(-letter(a)); }

Exponents exponent(const Word& word) {
    Exponents sum;
    for (auto a : word) {
        if (letter(a) == 1) ++sum.x;
        if (letter(a) == -1) --sum.x;
        if (letter(a) == 2) ++sum.y;
        if (letter(a) == -2) --sum.y;
    }
    return sum;
}

struct WordPool {
    std::unordered_map<Word, Id> known;
    std::vector<const Word*> words = {nullptr};
    std::vector<Exponents> sums = {{}};

    Id intern(Word word) {
        const Id next = words.size();
        const auto [it, created] = known.try_emplace(std::move(word), next);
        if (created) {
            if (next > id_mask) throw std::runtime_error("word ID guard");
            words.push_back(&it->first);
            sums.push_back(exponent(it->first));
        }
        return it->second;
    }

    Id find(const Word& word) const {
        const auto found = known.find(word);
        return found == known.end() ? 0 : found->second;
    }
};

Key key(State state) {
    std::sort(state.begin(), state.end());
    return state[0] | (Key(state[1]) << id_bits) | (Key(state[2]) << (2 * id_bits));
}

State decode(Key k) {
    return {Id(k & id_mask), Id((k >> id_bits) & id_mask), Id(k >> (2 * id_bits))};
}

struct Move {
    enum Kind { invert, multiply, conjugate } kind;
    unsigned slot;
    int factor;
    bool inverse_factor = false;
};

std::vector<Move> moves(unsigned rank) {
    std::vector<Move> active;
    for (unsigned i = 0; i < rank; ++i) {
        active.push_back({Move::invert, i, 0});
        for (unsigned j = 0; j < rank; ++j) if (i != j) {
            active.push_back({Move::multiply, i, int(j)});
            active.push_back({Move::multiply, i, int(j), true});
        }
        for (int a : {1, -1, 2, -2}) active.push_back({Move::conjugate, i, a});
    }
    return active;
}

Word changed(std::span<const Word* const> words, const Move& move) {
    const Word& w = *words[move.slot];
    switch (move.kind) {
        case Move::invert: {
            Word result;
            result.reserve(w.size());
            for (auto a = w.rbegin(); a != w.rend(); ++a) result.push_back(inverse(*a));
            return result;
        }
        case Move::multiply: {
            const Word& donor = *words[move.factor];
            const auto donor_letter = [&](size_t i) {
                return move.inverse_factor ? inverse(donor[donor.size() - 1 - i]) : donor[i];
            };
            size_t cancel = 0;
            while (cancel < std::min(w.size(), donor.size()) &&
                   w[w.size() - 1 - cancel] == inverse(donor_letter(cancel))) ++cancel;
            Word result;
            result.reserve(w.size() + donor.size() - 2 * cancel);
            result.append(w, 0, w.size() - cancel);
            for (size_t i = cancel; i < donor.size(); ++i) result.push_back(donor_letter(i));
            return result;
        }
        case Move::conjugate: {
            if (w.empty()) return w;
            const char a = static_cast<char>(move.factor);
            const bool first_cancels = w.front() == inverse(a);
            const bool last_cancels = w.back() == a;
            Word result;
            result.reserve(w.size() + 2);
            if (!first_cancels) result.push_back(a);
            result.append(w, first_cancels, w.size() - first_cancels - last_cancels);
            if (!last_cancels) result.push_back(inverse(a));
            return result;
        }
    }
    throw std::runtime_error("unknown move kind");
}

Exponents changed(const std::array<Exponents, 3>& sums, const Move& move) {
    Exponents here = sums[move.slot];
    switch (move.kind) {
        case Move::invert: return -here;
        case Move::multiply: return here + (move.inverse_factor ? -sums[move.factor] : sums[move.factor]);
        case Move::conjugate: return here;
    }
    throw std::runtime_error("unknown move kind");
}

struct Node {
    Key state;
    uint32_t parent;
    uint8_t via;
    uint8_t depth;
};

struct Ball {
    std::unordered_map<Key, uint32_t> seen;
    std::vector<Node> nodes;
};

void check_time(size_t counter) {
    if ((counter & 4095) == 0 && Clock::now() - start_time > std::chrono::seconds(22)) {
        throw std::runtime_error("elapsed time guard");
    }
}

Ball ball(State root, WordPool& pool, const std::vector<Move>& actions) {
    Ball result;
    const Key root_key = key(root);
    result.seen.emplace(root_key, 0);
    result.nodes.push_back({root_key, 0, 0, 0});
    std::array<size_t, max_depth + 1> counts = {1};
    for (size_t n = 0; n < result.nodes.size(); ++n) {
        check_time(n);
        const auto node = result.nodes[n];
        if (node.depth == max_depth) break;
        const State state = decode(node.state);
        const std::array<const Word*, 3> words = {pool.words[state[0]], pool.words[state[1]], pool.words[state[2]]};
        for (unsigned i = 0; i < actions.size(); ++i) {
            const auto& move = actions[i];
            State next = state;
            next[move.slot] = pool.intern(changed(words, move));
            const Key next_key = key(next);
            auto [entry, added] = result.seen.emplace(next_key, result.nodes.size());
            if (added) {
                ++counts[node.depth + 1];
                result.nodes.push_back({next_key, uint32_t(n), uint8_t(i), uint8_t(node.depth + 1)});
            }
        }
    }
    std::cout << "layers";
    for (auto count : counts) std::cout << ' ' << count;
    std::cout << ", words " << pool.known.size() << '\n';
    return result;
}

Key projection(State state, unsigned changed_slot, Exponents sum) {
    if (sum.x < -exp_bias || sum.x >= exp_bias || sum.y < -exp_bias || sum.y >= exp_bias) return 0;
    Id a = state[(changed_slot + 1) % 3], b = state[(changed_slot + 2) % 3];
    if (!a || !b) return 0;
    if (a > b) std::swap(a, b);
    return Key(a) | (Key(b) << id_bits) | (Key(sum.x + exp_bias) << (2 * id_bits)) |
           (Key(sum.y + exp_bias) << (2 * id_bits + 11));
}

std::string repr(const Word& word) {
    std::string result;
    for (auto a : word) {
        if (letter(a) == 1) result.push_back('x');
        if (letter(a) == -1) result.push_back('X');
        if (letter(a) == 2) result.push_back('y');
        if (letter(a) == -2) result.push_back('Y');
    }
    return result;
}

void print_state(const Ball& ball, uint32_t index, const WordPool& pool) {
    auto state = decode(ball.nodes[index].state);
    std::cout << '[' << repr(*pool.words[state[0]]) << ',' << repr(*pool.words[state[1]]) << ',' << repr(*pool.words[state[2]]) << ']';
}

void print_branch(const Ball& ball, uint32_t index, const WordPool& pool) {
    std::vector<uint32_t> nodes;
    while (index != 0) {
        nodes.push_back(index);
        index = ball.nodes[index].parent;
    }
    print_state(ball, 0, pool);
    for (auto it = nodes.rbegin(); it != nodes.rend(); ++it) {
        std::cout << " --" << unsigned(ball.nodes[*it].via) << "--> ";
        print_state(ball, *it, pool);
    }
    std::cout << '\n';
}

using ManyState = std::array<Id, 8>;

struct ManyHash {
    size_t operator()(const ManyState& state) const {
        size_t hash = 17;
        for (Id word : state) hash = hash * 1000003 + word;
        return hash;
    }
};

void sort_words(ManyState& words) {
    std::sort(words.begin(), words.end(), [](Id left, Id right) {
        return (left ? left : UINT32_MAX) < (right ? right : UINT32_MAX);
    });
}

std::unordered_set<ManyState, ManyHash> direct_ball(ManyState root, unsigned rank, unsigned radius,
                                                    WordPool& pool, const std::vector<Move>& actions) {
    sort_words(root);
    std::unordered_set<ManyState, ManyHash> seen = {root};
    std::vector<ManyState> layer = {root};
    size_t expanded = 0;
    std::cout << "layers 1";
    for (unsigned depth = 0; depth < radius; ++depth) {
        std::vector<ManyState> following;
        for (const auto& here : layer) {
            check_time(expanded++);
            std::array<const Word*, 8> words{};
            for (unsigned slot = 0; slot < rank; ++slot) words[slot] = pool.words[here[slot]];
            for (const auto& move : actions) {
                ManyState next = here;
                next[move.slot] = pool.intern(changed(words, move));
                sort_words(next);
                if (seen.insert(next).second) following.push_back(next);
            }
        }
        layer = std::move(following);
        std::cout << ' ' << layer.size();
    }
    std::cout << ", total " << seen.size() << '\n';
    return seen;
}

void direct_cases(unsigned minimum_adds) {
    for (unsigned adds = minimum_adds; adds <= 6; ++adds) {
        const unsigned rank = adds + 2;
        const unsigned radius = 6 - adds;
        WordPool pool;
        const Id empty = pool.intern(Word());
        const Id x = pool.intern(Word{1});
        const Id y = pool.intern(Word{2});
        const Id r1 = pool.intern(Word{char(-2), char(-2), 1, 2, 1});
        const Id r2 = pool.intern(Word{char(-2), char(-2), char(-1), 2, 1, 2, char(-1)});
        const auto actions = moves(rank);
        ManyState source{r1, r2}, target{x, y};
        std::fill(source.begin() + 2, source.begin() + rank, empty);
        std::fill(target.begin() + 2, target.begin() + rank, empty);
        std::cout << "adds " << adds << ", rank " << rank << ", radius " << radius
                  << ", actions " << actions.size() << '\n';
        std::cout << "forward ";
        const auto forward = direct_ball(source, rank, radius, pool, actions);
        std::cout << "reverse ";
        const auto reverse = direct_ball(target, rank, radius, pool, actions);
        size_t intersections = 0;
        for (const auto& state : reverse) if (forward.contains(state)) ++intersections;
        std::cout << "intersections " << intersections << '\n';
    }
}

int main(int argc, char** argv) try {
    const rlimit memory_guard{350ULL * 1024 * 1024, 350ULL * 1024 * 1024};
    if (setrlimit(RLIMIT_AS, &memory_guard) != 0) throw std::runtime_error("memory guard setup");
    if (argc == 2) {
        const std::string argument = argv[1];
        if (argument == "--direct" || argument == "--direct-all") {
            direct_cases(argument == "--direct-all" ? 0 : 1);
            return 0;
        }
    }
    if (argc != 1) throw std::runtime_error("expected no arguments, --direct, or --direct-all");
    WordPool pool;
    const auto actions = moves(3);
    const Id empty = pool.intern(Word());
    const Id x = pool.intern(Word{1});
    const Id y = pool.intern(Word{2});
    const Id r1 = pool.intern(Word{char(-2), char(-2), 1, 2, 1});
    const Id r2 = pool.intern(Word{char(-2), char(-2), char(-1), 2, 1, 2, char(-1)});
    const auto forward = ball({r1, r2, empty}, pool, actions);
    const auto reverse = ball({x, y, empty}, pool, actions);
    std::unordered_set<Key> projections;
    projections.reserve(forward.nodes.size() * 3);
    for (const Node& node : forward.nodes) {
        State state = decode(node.state);
        for (unsigned slot = 0; slot < 3; ++slot) {
            auto p = projection(state, slot, pool.sums[state[slot]]);
            if (p == 0) throw std::runtime_error("projection encoding guard");
            projections.insert(p);
        }
    }
    std::cout << "projections " << projections.size() << '\n';

    unsigned min_length = 11;
    uint64_t match_count = 0;
    uint32_t forward_end = 0, reverse_end = 0;
    unsigned edge_to_mid = 0, edge_from_mid = 0;
    std::array<std::string, 3> midpoint;
    bool has_midpoint = false;
    constexpr unsigned no_edge = 255;
    const auto match = [&](uint32_t f, uint32_t r, unsigned from_r, unsigned to_f,
                           const std::array<const Word*, 3>& mid) {
        const unsigned distance = forward.nodes[f].depth + reverse.nodes[r].depth +
            (from_r != no_edge) + (to_f != no_edge);
        ++match_count;
        if (distance >= min_length) return;
        min_length = distance;
        forward_end = f;
        reverse_end = r;
        edge_to_mid = from_r;
        edge_from_mid = to_f;
        has_midpoint = from_r != no_edge;
        if (has_midpoint) for (unsigned j = 0; j < 3; ++j) midpoint[j] = repr(*mid[j]);
    };

    uint64_t outer_edges = 0, exact_inner_edges = 0;
    for (uint32_t i = 0; i < reverse.nodes.size(); ++i) {
        check_time(i);
        const auto node = reverse.nodes[i];
        if (const auto it = forward.seen.find(node.state); it != forward.seen.end()) {
            match(it->second, i, no_edge, no_edge, {});
        }
        State right = decode(node.state);
        const std::array<const Word*, 3> right_words = {pool.words[right[0]], pool.words[right[1]], pool.words[right[2]]};
        for (unsigned m = 0; m < actions.size(); ++m) {
            ++outer_edges;
            const auto move = actions[m];
            const Word new_word = changed(right_words, move);
            State mid = right;
            mid[move.slot] = pool.find(new_word);
            auto mid_words = right_words;
            mid_words[move.slot] = &new_word;
            if (mid[move.slot]) {
                if (const auto it = forward.seen.find(key(mid)); it != forward.seen.end()) {
                    match(it->second, i, m, no_edge, mid_words);
                }
            }
            std::array<Exponents, 3> sums = {pool.sums[right[0]], pool.sums[right[1]], pool.sums[right[2]]};
            sums[move.slot] = mid[move.slot] ? pool.sums[mid[move.slot]] : exponent(new_word);
            for (unsigned n = 0; n < actions.size(); ++n) {
                const auto action = actions[n];
                if (!projections.contains(projection(mid, action.slot, changed(sums, action)))) continue;
                ++exact_inner_edges;
                State left = mid;
                left[action.slot] = pool.find(changed(mid_words, action));
                if (!left[action.slot]) continue;
                if (const auto it = forward.seen.find(key(left)); it != forward.seen.end()) {
                    match(it->second, i, m, n, mid_words);
                }
            }
        }
    }

    std::cout << "outer_edges " << outer_edges << ", exact_inner_edges " << exact_inner_edges
              << ", path_matches_with_duplicates " << match_count << '\n';
    if (!match_count) {
        std::cout << "distance >10 in the projected graph\n";
    } else {
        std::cout << "distance " << min_length << '\n';
        print_branch(forward, forward_end, pool);
        print_branch(reverse, reverse_end, pool);
        if (has_midpoint) {
            std::cout << "reverse boundary operations " << edge_to_mid << ' ' << edge_from_mid
                      << ", midpoint [" << midpoint[0] << ',' << midpoint[1] << ',' << midpoint[2] << "]\n";
        }
    }
    return 0;
} catch (const std::exception& exception) {
    std::cerr << "incomplete: " << exception.what() << '\n';
    return 1;
}
