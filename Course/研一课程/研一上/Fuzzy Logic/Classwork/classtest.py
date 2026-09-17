# Step 1: Input or define the fuzzy relation matrix
# Example:
# R = [[1, 0.8, 0.0, 0.1, 0.2],
# [0.8, 1.0, 0.4, 0.0, 0.91,
# [0.0, 0.4, 1.0, 0.0, 0.0],
# [0.1, 0.0, 0.0, 1.0, 0.5],
# [0.2, 0.9, 0.0, 0.5, 1.0]]
# Step 2: Check Reflexivity
# Hint: The matrix is reflexive if all diagonal elements are 1.
# Example: if R[i][i] = 1 for all i → Reflexive
# Step 3: Check Symmetry
# Hint: The matrix is symmetric if R[i][j] = R[j][i] for all i, j.
# Step 4: Check Transitivity
# Hint: Use max-min transitivity condition:
# For all i, j, k: R[il[k] ≥ min(R[i][j]], R[j][k])
# Step 5: Combine results
# Print whether the matrix is reflexive, symmetric, transitive
# and whether it is an equivalence matrix.
# Step 6: Optional - define helper functions for each property
# (reflexive_check, symmetric_check, transitive_check)
# and call them inside your main code.