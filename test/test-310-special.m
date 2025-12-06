Grid[{
    {
        Plot3D[Mod[Floor[x^2+y^2], 3], {x,-3,3}, {y,-3,3}, Axes->False, Boxed->False],
        Plot3D[FractionalPart[x y], {x,-2,2}, {y,-2,2}, Axes->False, Boxed->False],
        Plot3D[IntegerPart[x y], {x,-2,2}, {y,-2,2}, Axes->False, Boxed->False]
    }, {
        Plot3D[If[Floor[x^2+y^2]==2, 1, 0], {x,-2,2}, {y,-2,2}, Axes->False, Boxed->False],
        Plot3D[Which[Floor[x^2+y^2]==2, 1, Floor[x+0.5]==0, -1, True, 0], {x,-2,2}, {y,-2,2}, Axes->False, Boxed->False]
    }, {
        Plot3D[Min[x,y], {x,-2,2}, {y,-2,2}, Axes->False, Boxed->False],
        Plot3D[Max[x,y], {x,-2,2}, {y,-2,2}, Axes->False, Boxed->False]
    }
}]
