Manipulate[
    Plot[
        Abs[Zeta[x I + y]],
        {x,0,50},
        (*PlotPoints->200,*)
        PlotRange -> {Automatic, {0, 3}}
    ],
    {{y,0.5},0,.95,0.05}
]
