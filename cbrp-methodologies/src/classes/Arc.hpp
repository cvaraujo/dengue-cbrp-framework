//
// Created by Carlos on 06/07/2021.
//

#ifndef DPARP_ARC_H
#define DPARP_ARC_H

class Arc {
  private:
    int o_;      // origin node
    int d_;      // destination node
    int length_; // length of the arc
    int block_;  // block identifier

  public:
    Arc(int o, int d, int length, int block)
        : o_(o)
        , d_(d)
        , length_(length)
        , block_(block) {}

    // Getters
    [[nodiscard]] int getO() const { return o_; }
    [[nodiscard]] int getD() const { return d_; }
    [[nodiscard]] int getLength() const { return length_; }
    [[nodiscard]] int getBlock() const { return block_; }

    // Setters
    void setO(int o) { o_ = o; }
    void setD(int d) { d_ = d; }
    void setLength(int length) { length_ = length; }
    void setBlock(int block) { block_ = block; }
};

#endif // DPARP_ARC_H
