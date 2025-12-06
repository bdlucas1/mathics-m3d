Manipulate[
    Plot3D[
        Sin[x]*Cos[y]*a,
        {x,0,10}, {y,0,10},
        Axes -> {True,True,True},
        PlotRange -> {-2,2}
    ],
    {{a,1}, 0, 2, 0.1}
]
