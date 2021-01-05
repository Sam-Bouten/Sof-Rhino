import math


def get_principal_stresses(stress_dict):
    """Get principal stress eigenvalues and corresponding eigenvectors.
    
    Variables
    ---------
    stress_dict : dictionary
        Mapping from stress strings to values.

    Returns
    -------
    xn : number
        Implement Newton's method: compute the linear approximation
        of f(x) at xn and find x intercept by the formula
            x = xn - f(xn)/df(xn)
    
    """
    # unpack global coordinate stress components
    σx = stress_dict["σx"]  ; σy = stress_dict["σy"]  ; σz = stress_dict["σz"]
    τxy = stress_dict["τxy"]; τxz = stress_dict["τxz"]; τyz = stress_dict["τyz"]

    # stress invariants
    A = σx + σy + σz
    B = σx*σy + σx*σz + σy*σz - τxy**2 - τxz**2 - τyz**2
    C = σx*σy*σz + 2*τxy*τxz*τyz - σx*(τyz**2) - σy*(τxz**2) - σz*(τxy**2)

    # get first root by Newton's method solver
    σ_iv  = lambda p: p**3 - A*(p**2) + B*p - C
    dσ_iv = lambda p: 3*(p**2) - 2*A*p + B
    p1 = solve_newton(σ_iv, dσ_iv, max((σx, σy, σz)), 1E-5)

    # get remaining roots from analytical polynomial solver
    p2, p3 = solve_poly_deg2(1, (p1 - A), (p1**2 - p1*A + B))

    # order principal stresses
    σ1, σ2, σ3 = sorted([p1, p2, p3], reverse=True)

    return σ1, σ2, σ3


def solve_newton(f, df, x0, epsilon=1E-8, max_iter=100):
    """Approximate solution of f(x)=0 by Newton's method.

    Variables
    ---------
    f : callback function
        Function for which we are searching for a solution f(x)=0.

    df : callback function
        Derivative of f(x).

    x0 : number
        Initial guess for a solution f(x)=0.

    epsilon : number
        Stopping criteria is abs(f(x)) < epsilon.

    max_iter : integer
        Maximum number of iterations of Newton's method.
        By default set to: 100

    Returns
    -------
    xn : number
        Implement Newton's method: compute the linear approximation
        of f(x) at xn and find x intercept by the formula
            x = xn - f(xn)/df(xn)
    """
    xn = x0
    for n in range(0, max_iter):
        fxn = f(xn)
        if abs(fxn) < epsilon:
            return xn
        dfxn = df(xn)
        if dfxn == 0: # avoid zero derivatives
            xn = xn + 1E-3
            continue
        xn = xn - fxn / dfxn
    return None


def solve_poly_deg2(a, b, c):
    """Analitically solve polynomial of degree 2.

    Variables
    ---------
    a, b, c : number
        Coefficients of the equation a.x² + b.x + c

    Returns
    -------
    x1, x2 : tuple(number)
    """
    sq_D = math.sqrt(b**2 - 4*a*c)
    x1 = (-b + sq_D) / (2*a)
    x2 = (-b - sq_D) / (2*a)
    return x1, x2



if __name__ == "__main__":
    pass