# Big-O Complexity

Big-O describes the upper bound of an algorithm's growth rate. Common classes: O(1), O(log n), O(n), O(n log n), O(n^2), O(2^n).

# Binary Search

Binary search finds a target in a sorted array by repeatedly halving the search range. Time O(log n), space O(1) iteratively.

# Hash Tables

A hash table maps keys to buckets using a hash function. Average insert, lookup and delete are O(1); worst case O(n) with many collisions. Collisions are handled by chaining or open addressing.

# Quick Sort vs Merge Sort

Quick sort: average O(n log n), worst O(n^2), in-place, not stable. Merge sort: always O(n log n), needs O(n) extra space, stable.

# Dynamic Programming

DP solves problems with overlapping subproblems and optimal substructure by storing results (memoization or tabulation). Examples: Fibonacci, knapsack, LCS.
