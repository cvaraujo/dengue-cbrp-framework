
//
// Created by Carlos on 20/04/2024.
//

#ifndef SCBRP_KNAPSACK_H
#define SCBRP_KNAPSACK_H

#include <vector>

using namespace std;

class Knapsack {

  public:
    Knapsack() = default;

    static double Run(vector<int> &y, const vector<double> &cases, const vector<int> &time, int MT) {
        if (cases.size() <= 0 || MT <= 1)
            return 0;

        int i, w;
        int s = int(cases.size());
        double dp[s + 1][MT + 1];

        for (i = 0; i <= s; i++) {
            for (w = 0; w <= MT; w++) {
                if (i == 0 || w == 0)
                    dp[i][w] = 0;
                else if (time[i - 1] <= w)
                    dp[i][w] = max(dp[i - 1][w], dp[i - 1][w - time[i - 1]] + cases[i - 1]);
                else
                    dp[i][w] = dp[i - 1][w];
            }
        }

        // Retrieving the items
        w = MT;
        for (i = s; i > 0; i--) {
            if (dp[i][w] != dp[i - 1][w]) {
                y.push_back(i - 1);
                w -= time[i - 1];
            }
        }
        return dp[s][MT];
    }
};

#endif // SCBRP_KNAPSACK_H
