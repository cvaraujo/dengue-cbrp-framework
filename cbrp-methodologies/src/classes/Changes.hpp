//
// Created by Carlos on 27/05/2025.
//
#include "Parameters.hpp"
#include <utility>

#ifndef DPARP_CHANGES_H
#define DPARP_CHANGES_H

#pragma once

struct Change {
    double delta = 0.0;
    vector<pair<int, int_pair>> swaps;
    vector<int_pair> insertions;
    vector<int_pair> deletions;
};

class ChangeUtils {

  public:
    static Change createEmptyChange() {
        Change change;
        change.delta = 0.0;
        change.swaps.clear();
        change.insertions.clear();
        change.deletions.clear();
        return change;
    }

    static Change newChange(double delta) {
        Change change;
        change.delta = delta;
        change.swaps = vector<pair<int, int_pair>>();
        change.insertions = vector<int_pair>();
        change.deletions = vector<int_pair>();
        return change;
    }

    static Change newChange(double delta, vector<pair<int, int_pair>> swaps, vector<int_pair> insertions, vector<int_pair> deletions) {
        Change change;
        change.delta = delta;
        change.swaps = std::move(swaps);
        change.insertions = std::move(insertions);
        change.deletions = std::move(deletions);
        return change;
    }

    static Change newChange(double delta, vector<pair<int, int_pair>> swaps) {
        Change change;
        change.delta = delta;
        change.swaps = std::move(swaps);
        return change;
    }

    static bool isEmpty(const Change &change) {
        return (change.insertions.empty() && change.deletions.empty() && change.swaps.empty());
    }

    static void clear(Change &change) {
        change.delta = 0.0;
        change.swaps.clear();
        change.insertions.clear();
        change.deletions.clear();
    }

    // Add a swap
    static void addSwap(Change &change, int scenario, int to_remove, int to_insert) {
        change.swaps.emplace_back(scenario, int_pair{to_remove, to_insert});
    }

    // Add an insertion
    static void addInsertion(Change &change, int scenario, int to_insert) {
        change.insertions.emplace_back(scenario, to_insert);
    }

    // Add a deletion
    static void addDeletion(Change &change, int scenario, int to_remove) {
        change.deletions.emplace_back(scenario, to_remove);
    }

    static bool hasSwaps(const Change &change) {
        return !change.swaps.empty();
    }

    static bool hasInsertions(const Change &change) {
        return !change.insertions.empty();
    }

    static bool hasDeletions(const Change &change) {
        return !change.deletions.empty();
    }
}; // namespace ChangeUtils

#endif
