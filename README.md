# Z-score-algorithm
HFT trading alg and Longer time Frame. Read the README for more details
Introduction to Pairs Trading
What is Pairs Trading?
Pairs trading is an investment strategy that
capitalizes on the correlation between two
financial instruments(equities, futures,
crypto, etc). By identifying pairs of assets
with a strong historical correlation—typically
above 0.8—we can exploit pricing
inefficiencies. When one asset in a pair
deviates significantly in price relative to its
partner, we execute a trade: shorting the
overvalued asset and going long on the
undervalued one. This strategy hinges on
the premise that the prices will realign,
allowing us to profit from the convergence
while maintaining a market-neutral position.
From Broad Analysis to Precise
Execution
In my quest to redefine pairs trading, I start
with an expansive dataset: over 6,826
stocks. Our initial task is a comprehensive
analysis to identify potential pairs. This is
done by computing the correlation of every
stock against every other stock. That means
there are 6826!/2!(6826−2)! = 23,282,025 possible
combinations that must be computed. For
each correlation, I use a years’ worth of on
day prices meaning in total there are
23,282,025 x 255 prices pulled from an API
to calculate this. Such an awesome amount
of calculations requires powerful hardware
and algorithms. To complete all these
correlations, I use a multi parallel algorithm
running on a 32 core Intel CPU. Multi
parallelism, in this case, means instead of
starting at the beginning and going to the
end, I start at stock 1, 1000, 2000, 3000,
etc…simultaneously.
From Here, I only select pairs with a
correlation above .5. The reason for .5 is
because pairs trading does not work with a
low correlation. More importantly, the
correlation algorithm outputs 121,141
trading pairs with a correlation above .5,
which is more than enough
Determining Profitable Pairs using
Zscored Spreads
Each of those 121,141 pairs is back tested
using a proprietary z-score algorithm I
coded all by myself. The process goes like
this: for each pair, for example SPWR and
PLUG, pull 1 year worth of prices. These will
be two columns in a data set: i.e closing
price of PLUG and SPWR each day over
the past year. Then I create a new column
that is the spread between the two closing
prices of the stocks in the pair. From there, I
create a fourth and final column, the
Zscored spread. The is the z-score of the
spread across the entire year, each day
using a 40 day window. Meaning that the
current z-score of the spread is calculated
with the 40 day mean.
Now that the data is prepared, I back test
the pairs using my back testing algorithm.
This is a visual example of that back testing:
![image](https://github.com/user-attachments/assets/8ff30d2e-bd49-46e3-be3c-8d6dee60a627)

I make it so the program is not forward
looking and simulates what the strategy
would have done going back a year. In this
example, the pair is CLSK and RIOT. The
top redline represents a z-score of 1.5 and
the bottom a z-score of -1.5. When the blue
line, the z-scored spread, crosses above
1.5, the algorithm shorts CLSK and longs
RIOT. When the z-score is below -1.5, the
algorithm would short RIOT and long CLSK.
Beta is hedged for trades. The two green
lines represent a z-score of .5 and -.5
respectively. When the z-scored spreads
falls back into the range of .5 to -.5, the
algorithm exits the trade.
For each pair, the algorithm records the total
profit(trading with a simulated $10,000), hit
rate, standard deviation, and average profit.
Using another multi parallel algorithm, I use
the back testing method to back test all
121,141 pairs in a similar manner to the
multi parallel correlation algorithm. To be
frank, I did not have to pay for AC in my
apartment while running this because my
computers fans were running so hard. I
attached a document to this paper called
pair_trading_results_more_1d_1y.txt that
contains the results of all the pairs(DO NOT
SHARE THIS PLEASE).
Filtering Pairs
I take all those back tested pairs and filter
them. I create another text file that only has
pairs with a STD below 20%, hit rate above
.6, profit above 30% over a year
I then filter that file even more to only
include pairs where both stocks have an
average daily volume above 1 Million and a
market cap above 150 million. This reduces
the chance of data mining
Live Testing and Cash Trading
After I have the filtered pairs, I input them
into a trading algorithm I personally
developed using IBKR’s algorithmic trading
platform that works with Python and C. This
algorithm scans through all the pairs and
autonomously enters into trades for pairs
with a z-score above or below the threshold
of 1.5 and -1.5. The orders are sent to the
platform at 3:30 PM every day to be filled on
Market Close(MOC). The reason for MOC
orders is because that is where the liquidity
is now adays. The trading algorithm then
monitors the trades and exits them
autonomously when the exit threshold is
reached. At any given moment, there are
roughly 50 to 100 trades it has in the
portfolio although when I use real money
versus paper trading, I restrict it to pairs so
16 stocks(8 long 8 short). Please ask me for
the live demo of it running. I have done
many demos for people interested.
Author: Tommy Siracuse
Email: Siracuth@bc.edu
Phone: 703-489-9762
